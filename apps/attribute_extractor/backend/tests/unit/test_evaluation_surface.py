from __future__ import annotations

from research.steps.attribute_grouping.domain.models import AttrType
from research.steps.extraction.eval.models import EvalRow

from backend.app.services.exporting.accuracy import (
    EXCEL_LABELS,
    accuracy_surface,
    case_accuracy,
    excel_label,
    to_attr_type,
)


def _row(**kwargs) -> EvalRow:
    base = dict(
        eos_id=1,
        class_code="export",
        attr_id="a1",
        attr_name="A",
        attr_type=AttrType.NUMBER,
        gt_value=1.0,
        pred_value=1.0,
        value_match=True,
        is_match=True,
        match_method="number",
        base_label="TP",
        confidence_label="HC",
        extraction_error=False,
    )
    base.update(kwargs)
    return EvalRow(**base)


def test_case_accuracy_none_when_empty():
    assert case_accuracy(0, 0) is None
    assert case_accuracy(1, 2) == 0.5


def test_to_attr_type_fallback():
    assert to_attr_type("number") is AttrType.NUMBER
    assert to_attr_type("not-a-type") is AttrType.STRING


def test_excel_label_map():
    assert EXCEL_LABELS["FP_1"] == "FP1"
    assert excel_label("FP_2") == "FP2"


def test_accuracy_surface_groups_confidence():
    rows = [
        _row(attr_id="a", confidence_label="HC", is_match=True, base_label="TP"),
        _row(attr_id="b", confidence_label="HC", is_match=False, base_label="FP_2"),
        _row(attr_id="c", confidence_label="LC", is_match=True, base_label="TN", gt_value=None, pred_value=None),
        _row(attr_id="d", confidence_label="LC", is_match=False, base_label="FN", pred_value=None, extraction_error=True),
    ]
    surface = accuracy_surface(rows)
    assert surface["n_cases"] == 4
    assert surface["error_count"] == 1
    assert surface["accuracy"] == 0.5
    assert surface["high_confidence"] == {"n": 2, "accuracy": 0.5}
    assert surface["low_confidence"] == {"n": 2, "accuracy": 0.5}
