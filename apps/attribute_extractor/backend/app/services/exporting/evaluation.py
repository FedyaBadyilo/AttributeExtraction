"""Ground-truth export evaluation (same logic as the original MVP).

Bridges task export maps → ``research.steps.extraction.eval`` matching / LLM
judges / labels, then reshapes metrics for the Excel auto-metrics sheet.
"""

from __future__ import annotations

import logging
from typing import Any

from infra.config import get_config_and_env
from infra.llm_observability.langfuse import get_langfuse_handler
from research.steps.extraction.eval.judge_cases import (
    collect_string_judge_cases,
    collect_unit_judge_cases,
    resolve_string_judges,
    resolve_unit_judges,
)
from research.steps.extraction.eval.judges import LLMStringJudge, LLMUnitJudge
from research.steps.extraction.eval.models import (
    EvalAttribute,
    GroundTruthSlot,
    PredictionSlot,
)
from research.steps.extraction.eval.rows import build_eval_rows

from backend.app.pipeline.runner import PipelineTzResult
from backend.app.schemas import TzPackageRead
from backend.app.services.exporting.accuracy import accuracy_surface, excel_label, to_attr_type
from backend.app.services.exporting.common import package_recpart
from backend.app.services.exporting.models import AttributeColumn, ExportEvaluation
from backend.app.services.exporting.prediction_maps import fill_missing_eval_cases, prediction_maps_for_eval

logger = logging.getLogger(__name__)


def evaluate_with_ground_truth(
    packages: list[TzPackageRead],
    result_by_package: dict[str, PipelineTzResult],
    attrs: list[AttributeColumn],
    gt_maps: tuple[dict[tuple[str, str], Any], dict[tuple[str, str], str | None]],
) -> ExportEvaluation:
    gt_value_map, gt_unit_map = gt_maps
    pred_value_map, pred_unit_map, high_confidence_map, raw_quote_map, error_keys = prediction_maps_for_eval(
        packages,
        result_by_package,
    )
    eval_attrs = [attr for attr in attrs if attr.for_extraction]
    eval_cases = [(package_recpart(package), attr.attr_id) for package in packages for attr in eval_attrs]

    fill_missing_eval_cases(
        eval_cases=eval_cases,
        gt_value_map=gt_value_map,
        pred_value_map=pred_value_map,
        gt_unit_map=gt_unit_map,
        pred_unit_map=pred_unit_map,
        high_confidence_map=high_confidence_map,
        raw_quote_map=raw_quote_map,
    )

    universe, gt_index, predictions_by_eos, eos_to_recpart = _build_research_eval_inputs(
        packages=packages,
        eval_attrs=eval_attrs,
        gt_value_map=gt_value_map,
        gt_unit_map=gt_unit_map,
        pred_value_map=pred_value_map,
        pred_unit_map=pred_unit_map,
        high_confidence_map=high_confidence_map,
        raw_quote_map=raw_quote_map,
        error_keys=error_keys,
    )

    string_verdicts, unit_verdicts = _run_llm_judges(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions_by_eos,
    )
    rows = build_eval_rows(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions_by_eos,
        string_verdicts=string_verdicts,
        unit_verdicts=unit_verdicts,
        unit_matching_enabled=True,
    )

    labels_by_recpart: dict[str, dict[str, str]] = {recpart: {} for recpart in eos_to_recpart.values()}
    for row in rows:
        recpart = eos_to_recpart[row.eos_id]
        labels_by_recpart[recpart][row.attr_id] = excel_label(row.base_label)

    return ExportEvaluation(
        labels_by_recpart=labels_by_recpart,
        metrics={"extraction_surface": accuracy_surface(rows)},
    )


def _build_research_eval_inputs(
    *,
    packages: list[TzPackageRead],
    eval_attrs: list[AttributeColumn],
    gt_value_map: dict[tuple[str, str], Any],
    gt_unit_map: dict[tuple[str, str], str | None],
    pred_value_map: dict[tuple[str, str], Any],
    pred_unit_map: dict[tuple[str, str], str | None],
    high_confidence_map: dict[tuple[str, str], bool | None],
    raw_quote_map: dict[tuple[str, str], str | None],
    error_keys: frozenset[tuple[str, str]],
) -> tuple[
    list[EvalAttribute],
    dict[tuple[int, str], GroundTruthSlot],
    dict[int, dict[str, PredictionSlot]],
    dict[int, str],
]:
    universe: list[EvalAttribute] = []
    gt_index: dict[tuple[int, str], GroundTruthSlot] = {}
    predictions_by_eos: dict[int, dict[str, PredictionSlot]] = {}
    eos_to_recpart: dict[int, str] = {}

    for eos_id, package in enumerate(packages, start=1):
        recpart = package_recpart(package)
        eos_to_recpart[eos_id] = recpart
        predictions_by_eos[eos_id] = {}
        for attr in eval_attrs:
            key = (recpart, attr.attr_id)
            universe.append(
                EvalAttribute(
                    eos_id=eos_id,
                    class_code="export",
                    attr_id=attr.attr_id,
                    attr_name=attr.attr_name,
                    attr_type=to_attr_type(attr.value_type),
                    has_unit=attr.has_unit,
                )
            )
            gt_index[(eos_id, attr.attr_id)] = GroundTruthSlot(
                eos_id=eos_id,
                attr_id=attr.attr_id,
                attr_name=attr.attr_name,
                value=gt_value_map.get(key),
                unit=gt_unit_map.get(key),
            )
            predictions_by_eos[eos_id][attr.attr_id] = PredictionSlot(
                eos_id=eos_id,
                attr_id=attr.attr_id,
                value=pred_value_map.get(key),
                unit=pred_unit_map.get(key),
                raw_quote=raw_quote_map.get(key),
                high_confidence=high_confidence_map.get(key),
                error=key in error_keys,
            )

    return universe, gt_index, predictions_by_eos, eos_to_recpart


def _run_llm_judges(
    *,
    universe: list[EvalAttribute],
    gt_index: dict[tuple[int, str], GroundTruthSlot],
    predictions_by_eos: dict[int, dict[str, PredictionSlot]],
) -> tuple[dict[tuple[int, str], bool], dict[tuple[int, str], bool]]:
    config = get_config_and_env()
    max_workers = int(config.get("EXTRACTION", {}).get("max_concurrent_requests", 5) or 5)
    langfuse_handler = get_langfuse_handler()
    callbacks = [langfuse_handler] if langfuse_handler is not None else []

    string_cases = collect_string_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions_by_eos,
    )
    unit_cases = collect_unit_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions_by_eos,
        unit_matching_enabled=True,
    )

    string_verdicts: dict[tuple[int, str], bool] = {}
    unit_verdicts: dict[tuple[int, str], bool] = {}
    if string_cases:
        logger.info("GT export: running string judge on %s cases", len(string_cases))
        string_verdicts = resolve_string_judges(
            string_cases,
            LLMStringJudge(callbacks=callbacks),
            max_workers=max_workers,
        )
    if unit_cases:
        logger.info("GT export: running unit judge on %s cases", len(unit_cases))
        unit_verdicts = resolve_unit_judges(
            unit_cases,
            LLMUnitJudge(callbacks=callbacks),
            max_workers=max_workers,
        )
    return string_verdicts, unit_verdicts
