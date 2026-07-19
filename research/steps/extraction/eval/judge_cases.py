from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from research.steps.extraction.eval.matching import needs_string_judge, needs_unit_judge
from research.steps.extraction.eval.models import (
    EvalAttribute,
    GroundTruthSlot,
    PredictionSlot,
    SlotKey,
    StringJudgeCase,
    UnitJudgeCase,
)

StringJudge = Callable[[StringJudgeCase], bool]
UnitJudge = Callable[[UnitJudgeCase], bool]
_JudgeCaseT = TypeVar("_JudgeCaseT")


def _slot_key(eos_id: int, attr_id: str) -> SlotKey:
    return eos_id, attr_id


def collect_string_judge_cases(
    *,
    universe: list[EvalAttribute],
    gt_index: dict[SlotKey, GroundTruthSlot],
    predictions_by_eos: dict[int, dict[str, PredictionSlot]],
) -> list[StringJudgeCase]:
    cases: list[StringJudgeCase] = []
    for slot in universe:
        key = _slot_key(slot.eos_id, slot.attr_id)
        gt = gt_index[key]
        pred = predictions_by_eos[slot.eos_id][slot.attr_id]
        if not needs_string_judge(
            gt_value=gt.value,
            pred_value=pred.value,
            attr_type=slot.attr_type,
        ):
            continue
        cases.append(
            StringJudgeCase(
                eos_id=slot.eos_id,
                attr_id=slot.attr_id,
                attr_name=slot.attr_name,
                gt_value=str(gt.value),
                pred_value=str(pred.value),
                raw_quote=pred.raw_quote,
            )
        )
    return cases


def collect_unit_judge_cases(
    *,
    universe: list[EvalAttribute],
    gt_index: dict[SlotKey, GroundTruthSlot],
    predictions_by_eos: dict[int, dict[str, PredictionSlot]],
    unit_matching_enabled: bool,
) -> list[UnitJudgeCase]:
    if not unit_matching_enabled:
        return []

    cases: list[UnitJudgeCase] = []
    for slot in universe:
        key = _slot_key(slot.eos_id, slot.attr_id)
        gt = gt_index[key]
        pred = predictions_by_eos[slot.eos_id][slot.attr_id]
        if not needs_unit_judge(
            gt_value=gt.value,
            pred_value=pred.value,
            gt_unit=gt.unit,
            pred_unit=pred.unit,
            has_unit=slot.has_unit,
            unit_matching_enabled=unit_matching_enabled,
        ):
            continue
        gt_unit = gt.unit
        pred_unit = pred.unit
        if gt_unit is None or pred_unit is None:
            raise ValueError(
                "needs_unit_judge selected a slot with null unit: "
                f"eos_id={slot.eos_id}, attr_id={slot.attr_id}"
            )
        cases.append(
            UnitJudgeCase(
                eos_id=slot.eos_id,
                attr_id=slot.attr_id,
                attr_name=slot.attr_name,
                gt_unit=gt_unit,
                pred_unit=pred_unit,
            )
        )
    return cases


def _resolve_judge_cases(
    cases: list[_JudgeCaseT],
    judge: Callable[[_JudgeCaseT], bool],
    *,
    max_workers: int,
    key_fn: Callable[[_JudgeCaseT], SlotKey],
) -> dict[SlotKey, bool]:
    if not cases:
        return {}

    def _run_one(case: _JudgeCaseT) -> tuple[SlotKey, bool]:
        last_exc: BaseException | None = None
        for attempt in range(4):
            try:
                return key_fn(case), judge(case)
            except Exception as exc:  # noqa: BLE001 — transient LLM 5xx during eval
                last_exc = exc
                name = type(exc).__name__
                if "InternalServerError" not in name and "APIConnectionError" not in name:
                    raise
                if attempt == 3:
                    break
                time.sleep(1.5 * (attempt + 1))
        assert last_exc is not None
        raise last_exc

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        pairs = list(executor.map(_run_one, cases))
    return dict(pairs)


def resolve_string_judges(
    cases: list[StringJudgeCase],
    judge: StringJudge,
    *,
    max_workers: int,
) -> dict[SlotKey, bool]:
    return _resolve_judge_cases(
        cases,
        judge,
        max_workers=max_workers,
        key_fn=lambda case: _slot_key(case.eos_id, case.attr_id),
    )


def resolve_unit_judges(
    cases: list[UnitJudgeCase],
    judge: UnitJudge,
    *,
    max_workers: int,
) -> dict[SlotKey, bool]:
    return _resolve_judge_cases(
        cases,
        judge,
        max_workers=max_workers,
        key_fn=lambda case: _slot_key(case.eos_id, case.attr_id),
    )
