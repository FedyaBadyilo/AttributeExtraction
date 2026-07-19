from __future__ import annotations

import pytest

from research.steps.attribute_grouping.domain.models import AttrType
from research.steps.extraction.eval.matching import (
    confidence_label,
    label_for_case,
    match_values,
)
def test_label_for_case() -> None:
    assert label_for_case(None, None, True) == "TN"
    assert label_for_case(None, "x", False) == "FP_1"
    assert label_for_case("x", None, False) == "FN"
    assert label_for_case("x", "x", True) == "TP"
    assert label_for_case("x", "y", False) == "FP_2"


def test_confidence_label_maps_none_to_lc() -> None:
    assert confidence_label(True) == "HC"
    assert confidence_label(False) == "LC"
    assert confidence_label(None) == "LC"


def test_number_match() -> None:
    result = match_values(gt_value="10", pred_value=10, attr_type=AttrType.NUMBER)

    assert result.is_match
    assert result.match_method == "number_exact"


def test_range_match() -> None:
    result = match_values(gt_value=[0, 300], pred_value=[0, 300], attr_type=AttrType.RANGE)

    assert result.is_match
    assert result.match_method == "range_exact"


def test_number_match_rejects_invalid_gt() -> None:
    with pytest.raises(ValueError):
        match_values(gt_value="not-a-number", pred_value=10, attr_type=AttrType.NUMBER)


def test_enum_list_match_ignores_order() -> None:
    result = match_values(
        gt_value=["под золотник", "на золотник"],
        pred_value=["на золотник", "под золотник"],
        attr_type=AttrType.ENUM_LIST,
    )

    assert result.is_match


def test_string_judge_used_for_complex_string() -> None:
    result = match_values(
        gt_value="Общество с ограниченной ответственностью Ромашка",
        pred_value="ООО Ромашка",
        attr_type=AttrType.STRING,
        string_judge_verdict=True,
    )

    assert result.is_match
    assert result.string_judge_used
    assert result.match_method == "string_llm_judge"


def test_unit_matching_disabled_leaves_unit_match_null() -> None:
    result = match_values(
        gt_value=10,
        pred_value=10,
        attr_type=AttrType.NUMBER,
        gt_unit="кг",
        pred_unit="г",
        unit_matching_enabled=False,
        has_unit=True,
    )

    assert result.is_match
    assert result.unit_match is None


def test_unit_matching_skipped_when_attr_has_no_units() -> None:
    result = match_values(
        gt_value=10,
        pred_value=10,
        attr_type=AttrType.NUMBER,
        gt_unit=None,
        pred_unit="кг",
        unit_matching_enabled=True,
        has_unit=False,
    )

    assert result.is_match
    assert result.unit_match is None


def test_unit_matching_requires_pred_unit_when_gt_unit_set() -> None:
    match = match_values(
        gt_value=10,
        pred_value=10,
        attr_type=AttrType.NUMBER,
        gt_unit="кг",
        pred_unit="кг",
        unit_matching_enabled=True,
        has_unit=True,
    )
    mismatch = match_values(
        gt_value=10,
        pred_value=10,
        attr_type=AttrType.NUMBER,
        gt_unit="кг",
        pred_unit="г",
        unit_matching_enabled=True,
        has_unit=True,
    )
    missing_pred = match_values(
        gt_value=10,
        pred_value=10,
        attr_type=AttrType.NUMBER,
        gt_unit="кг",
        pred_unit=None,
        unit_matching_enabled=True,
        has_unit=True,
    )

    assert match.is_match and match.unit_match is True
    assert match.unit_match_method == "unit_casefold_exact"
    assert not mismatch.is_match and mismatch.unit_match is False
    assert mismatch.unit_match_method == "unit_mismatch"
    assert not missing_pred.is_match and missing_pred.unit_match is False
    assert missing_pred.unit_match_method == "unit_mismatch"


def test_unit_matching_fails_fast_when_gt_unit_missing_for_unit_attr() -> None:
    with pytest.raises(ValueError, match="non-null gt_unit"):
        match_values(
            gt_value=10,
            pred_value=10,
            attr_type=AttrType.NUMBER,
            gt_unit=None,
            pred_unit="кг",
            unit_matching_enabled=True,
            has_unit=True,
        )


def test_unit_normalized_matches_without_judge() -> None:
    cases = [
        ("°С", "⁰C"),
        ("м^3", "м³"),
        ("мес", "месяц"),
        ("кг/м^3", "кг/м³"),
        ("pH", "ед. pH"),
    ]
    for gt_unit, pred_unit in cases:
        result = match_values(
            gt_value=10,
            pred_value=10,
            attr_type=AttrType.NUMBER,
            gt_unit=gt_unit,
            pred_unit=pred_unit,
            unit_matching_enabled=True,
            has_unit=True,
        )
        assert result.is_match, (gt_unit, pred_unit)
        assert result.unit_match is True
        assert result.unit_match_method == "unit_normalized"
        assert not result.unit_judge_used


def test_unit_judge_verdict_overrides_mismatch() -> None:
    result = match_values(
        gt_value=10,
        pred_value=10,
        attr_type=AttrType.NUMBER,
        gt_unit="кг",
        pred_unit="килограмм",
        unit_matching_enabled=True,
        has_unit=True,
        unit_judge_verdict=True,
    )

    assert result.is_match
    assert result.unit_match is True
    assert result.unit_judge_used
    assert result.unit_match_method == "unit_llm_judge"
    assert result.match_method == "number_exact"
