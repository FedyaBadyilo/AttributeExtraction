from __future__ import annotations

from research.steps.extraction.eval.data import (
    build_eval_universe,
    build_ground_truth_index,
)
from research.steps.extraction.eval.judge_cases import (
    collect_string_judge_cases,
    collect_unit_judge_cases,
    resolve_string_judges,
    resolve_unit_judges,
)
from research.steps.extraction.eval.models import PredictionSlot, StringJudgeCase, UnitJudgeCase
from research.steps.extraction.eval.rows import build_eval_rows


def _raw_attr(attr_id: str, attr_name: str) -> dict:
    return {
        "attr_id": attr_id,
        "attr_name": attr_name,
        "descr": None,
        "attr_type": "Строка",
        "for_extraction": True,
        "units": None,
        "allowed_values": None,
    }


def test_collect_and_resolve_string_judges() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {"c1": [_raw_attr("a1", "A1")]},
    )
    gt_index = build_ground_truth_index([
        {
            "gid": 1,
            "attr_id": "a1",
            "attr_name": "A1",
            "value": "Общество с ограниченной ответственностью Ромашка",
        },
    ])
    predictions = {
        1: {
            "a1": PredictionSlot(
                eos_id=1,
                attr_id="a1",
                value="ООО Ромашка",
                high_confidence=True,
            ),
        },
    }

    cases = collect_string_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
    )
    assert len(cases) == 1
    assert cases[0].attr_id == "a1"

    calls: list[StringJudgeCase] = []

    def fake_judge(case: StringJudgeCase) -> bool:
        calls.append(case)
        return True

    verdicts = resolve_string_judges(cases, fake_judge, max_workers=2)
    rows = build_eval_rows(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
        string_verdicts=verdicts,
    )

    assert len(calls) == 1
    assert rows[0].is_match
    assert rows[0].match_method == "string_llm_judge"
    assert rows[0].base_label == "TP"


def test_collect_skips_deterministic_string_match() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {"c1": [_raw_attr("a1", "A1")]},
    )
    gt_index = build_ground_truth_index([
        {"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": "same"},
    ])
    predictions = {
        1: {
            "a1": PredictionSlot(
                eos_id=1,
                attr_id="a1",
                value="SAME",
                high_confidence=True,
            ),
        },
    }

    cases = collect_string_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
    )

    assert cases == []


def test_collect_skips_non_string_attr_types() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {
            "c1": [{
                "attr_id": "a1",
                "attr_name": "A1",
                "descr": None,
                "attr_type": "Вещественное число",
                "for_extraction": True,
                "units": None,
                "allowed_values": None,
            }],
        },
    )
    gt_index = build_ground_truth_index([
        {"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": "1"},
    ])
    predictions = {
        1: {
            "a1": PredictionSlot(
                eos_id=1,
                attr_id="a1",
                value=2,
                high_confidence=True,
            ),
        },
    }

    cases = collect_string_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
    )

    assert cases == []


def test_collect_and_resolve_unit_judges() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {
            "c1": [{
                "attr_id": "a1",
                "attr_name": "A1",
                "descr": None,
                "attr_type": "Вещественное число",
                "for_extraction": True,
                "units": ["кг", "г"],
                "allowed_values": None,
            }],
        },
    )
    gt_index = build_ground_truth_index([
        {
            "gid": 1,
            "attr_id": "a1",
            "attr_name": "A1",
            "value": 10,
            "unit": "килограмм",
        },
    ])
    predictions = {
        1: {
            "a1": PredictionSlot(
                eos_id=1,
                attr_id="a1",
                value=10,
                unit="кг",
                high_confidence=True,
            ),
        },
    }

    cases = collect_unit_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
        unit_matching_enabled=True,
    )
    assert len(cases) == 1
    assert cases[0].gt_unit == "килограмм"
    assert cases[0].pred_unit == "кг"

    calls: list[UnitJudgeCase] = []

    def fake_judge(case: UnitJudgeCase) -> bool:
        calls.append(case)
        return True

    verdicts = resolve_unit_judges(cases, fake_judge, max_workers=2)
    rows = build_eval_rows(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
        unit_verdicts=verdicts,
        unit_matching_enabled=True,
    )

    assert len(calls) == 1
    assert rows[0].is_match
    assert rows[0].unit_match is True
    assert rows[0].unit_judge_used
    assert rows[0].unit_match_method == "unit_llm_judge"
    assert rows[0].match_method == "number_exact"
    assert rows[0].base_label == "TP"


def test_collect_unit_skips_normalized_match() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {
            "c1": [{
                "attr_id": "a1",
                "attr_name": "A1",
                "descr": None,
                "attr_type": "Вещественное число",
                "for_extraction": True,
                "units": ["°С"],
                "allowed_values": None,
            }],
        },
    )
    gt_index = build_ground_truth_index([
        {"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": 45, "unit": "°С"},
    ])
    predictions = {
        1: {
            "a1": PredictionSlot(
                eos_id=1,
                attr_id="a1",
                value=45,
                unit="⁰C",
                high_confidence=True,
            ),
        },
    }

    cases = collect_unit_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
        unit_matching_enabled=True,
    )
    assert cases == []


def test_collect_unit_disabled_when_unit_matching_off() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {
            "c1": [{
                "attr_id": "a1",
                "attr_name": "A1",
                "descr": None,
                "attr_type": "Вещественное число",
                "for_extraction": True,
                "units": ["кг"],
                "allowed_values": None,
            }],
        },
    )
    gt_index = build_ground_truth_index([
        {"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": 10, "unit": "кг"},
    ])
    predictions = {
        1: {
            "a1": PredictionSlot(
                eos_id=1,
                attr_id="a1",
                value=10,
                unit="г",
                high_confidence=True,
            ),
        },
    }

    cases = collect_unit_judge_cases(
        universe=universe,
        gt_index=gt_index,
        predictions_by_eos=predictions,
        unit_matching_enabled=False,
    )
    assert cases == []
