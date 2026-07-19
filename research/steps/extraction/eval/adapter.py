from __future__ import annotations

from pathlib import Path

import mlflow
import pandas as pd
from infra.config import get_config_and_env
from infra.llm.callbacks import CompletionProgressCallback
from infra.llm_observability.langfuse import get_langfuse_handler
from infra.research_eval.types import BaseEvalAdapter, EvalResult
from research.datasets.access import (
    GROUND_TRUTH_FILENAME,
    PROCESSED_DIR,
    load_class_attribute_sets,
    load_examples_manifest,
    load_ground_truth,
)
from research.steps.extraction.eval.artifacts import write_artifacts
from research.steps.extraction.eval.data import (
    build_eval_universe,
    build_ground_truth_index,
    load_predictions_for_universe,
)
from research.steps.extraction.eval.judge_cases import (
    StringJudge,
    UnitJudge,
    collect_string_judge_cases,
    collect_unit_judge_cases,
    resolve_string_judges,
    resolve_unit_judges,
)
from research.steps.extraction.eval.judges import LLMStringJudge, LLMUnitJudge
from research.steps.extraction.eval.metrics import compute_metrics
from research.steps.extraction.eval.models import (
    EvalSummary,
    SlotKey,
    StringJudgeCase,
    UnitJudgeCase,
)
from research.steps.extraction.eval.params import pipeline_params_from_config
from research.steps.extraction.eval.rows import build_eval_rows

_UNIT_MATCHING_DISABLED_NOTE = (
    "Unit matching is disabled. Enable with --unit-matching when "
    "ground_truth.jsonl rows include an explicit unit field."
)
_UNIT_MATCHING_ENABLED_NOTE = (
    "Unit matching enabled only for attributes with units: when both values are "
    "non-null, gt_unit must be set and is compared to pred_unit "
    "(deterministic normalize, then LLM unit judge on remaining mismatches)."
)


class ExtractionEvalAdapter(BaseEvalAdapter):
    target = "nsi-attribute-extraction"

    def __init__(
        self,
        *,
        string_judge: StringJudge | None = None,
        use_default_string_judge: bool = True,
        unit_judge: UnitJudge | None = None,
        use_default_unit_judge: bool = True,
        unit_matching_enabled: bool = False,
    ) -> None:
        self._string_judge = string_judge
        self._use_default_string_judge = use_default_string_judge
        self._unit_judge = unit_judge
        self._use_default_unit_judge = use_default_unit_judge
        self._unit_matching_enabled = unit_matching_enabled

    def _resolve_string_verdicts(
        self,
        string_cases: list[StringJudgeCase],
        *,
        max_workers: int,
    ) -> tuple[dict[SlotKey, bool], int]:
        if not string_cases:
            return {}, 0

        if self._string_judge is not None:
            verdicts = resolve_string_judges(
                string_cases,
                self._string_judge,
                max_workers=max_workers,
            )
            return verdicts, len(string_cases)

        langfuse_handler = get_langfuse_handler()
        with CompletionProgressCallback(
            len(string_cases),
            desc="Eval string judge",
            unit="case",
        ) as progress:
            callbacks = [h for h in [langfuse_handler, progress] if h is not None]
            llm_judge = LLMStringJudge(callbacks=callbacks)
            verdicts = resolve_string_judges(
                string_cases,
                llm_judge,
                max_workers=max_workers,
            )
        return verdicts, llm_judge.call_count

    def _resolve_unit_verdicts(
        self,
        unit_cases: list[UnitJudgeCase],
        *,
        max_workers: int,
    ) -> tuple[dict[SlotKey, bool], int]:
        if not unit_cases:
            return {}, 0

        if self._unit_judge is not None:
            verdicts = resolve_unit_judges(
                unit_cases,
                self._unit_judge,
                max_workers=max_workers,
            )
            return verdicts, len(unit_cases)

        langfuse_handler = get_langfuse_handler()
        with CompletionProgressCallback(
            len(unit_cases),
            desc="Eval unit judge",
            unit="case",
        ) as progress:
            callbacks = [h for h in [langfuse_handler, progress] if h is not None]
            llm_judge = LLMUnitJudge(callbacks=callbacks)
            verdicts = resolve_unit_judges(
                unit_cases,
                llm_judge,
                max_workers=max_workers,
            )
        return verdicts, llm_judge.call_count

    def evaluate(self, source: str | Path) -> EvalResult:
        source_dir = Path(source)
        examples = load_examples_manifest()
        universe = build_eval_universe(examples, load_class_attribute_sets())
        ground_truth_rows = load_ground_truth()
        if self._unit_matching_enabled and ground_truth_rows:
            if not any("unit" in row for row in ground_truth_rows):
                raise ValueError(
                    "unit_matching_enabled=True requires ground_truth.jsonl rows "
                    "with an explicit 'unit' field"
                )
        gt_index = build_ground_truth_index(ground_truth_rows)
        eos_ids = sorted({slot.eos_id for slot in universe})
        predictions_by_eos = load_predictions_for_universe(source_dir, eos_ids)

        string_cases = collect_string_judge_cases(
            universe=universe,
            gt_index=gt_index,
            predictions_by_eos=predictions_by_eos,
        )
        string_verdicts: dict[SlotKey, bool] = {}
        string_judge_call_count = 0
        string_judge_enabled = (
            self._use_default_string_judge or self._string_judge is not None
        )

        unit_judge_enabled = self._unit_matching_enabled and (
            self._use_default_unit_judge or self._unit_judge is not None
        )
        unit_cases = collect_unit_judge_cases(
            universe=universe,
            gt_index=gt_index,
            predictions_by_eos=predictions_by_eos,
            unit_matching_enabled=self._unit_matching_enabled,
        )
        unit_verdicts: dict[SlotKey, bool] = {}
        unit_judge_call_count = 0

        need_string_judge = bool(string_cases and string_judge_enabled)
        need_unit_judge = bool(unit_cases and unit_judge_enabled)
        if need_string_judge or need_unit_judge:
            needs_llm_config = (
                (need_string_judge and self._string_judge is None)
                or (need_unit_judge and self._unit_judge is None)
            )
            if needs_llm_config:
                config = get_config_and_env()
                max_workers = int(config["EXTRACTION"]["max_concurrent_requests"])
            else:
                max_workers = 8
            if need_string_judge:
                string_verdicts, string_judge_call_count = self._resolve_string_verdicts(
                    string_cases,
                    max_workers=max_workers,
                )
            if need_unit_judge:
                unit_verdicts, unit_judge_call_count = self._resolve_unit_verdicts(
                    unit_cases,
                    max_workers=max_workers,
                )

        rows = build_eval_rows(
            universe=universe,
            gt_index=gt_index,
            predictions_by_eos=predictions_by_eos,
            string_verdicts=string_verdicts or None,
            unit_verdicts=unit_verdicts or None,
            unit_matching_enabled=self._unit_matching_enabled,
        )

        metrics = compute_metrics(rows)
        summary = EvalSummary(
            unit_matching_enabled=self._unit_matching_enabled,
            unit_matching_note=(
                _UNIT_MATCHING_ENABLED_NOTE
                if self._unit_matching_enabled
                else _UNIT_MATCHING_DISABLED_NOTE
            ),
            string_judge_enabled=string_judge_enabled,
            string_judge_call_count=string_judge_call_count,
            unit_judge_enabled=unit_judge_enabled,
            unit_judge_call_count=unit_judge_call_count,
            source=str(source_dir),
        )
        artifacts = write_artifacts(rows=rows, summary=summary)
        params = pipeline_params_from_config()
        mlflow.log_input(
            mlflow.data.from_pandas(
                pd.DataFrame(ground_truth_rows),
                source=str(PROCESSED_DIR / GROUND_TRUTH_FILENAME),
                name="extraction_ground_truth",
            ),
            context="eval",
        )
        return EvalResult(metrics=metrics, params=params, artifacts=artifacts)
