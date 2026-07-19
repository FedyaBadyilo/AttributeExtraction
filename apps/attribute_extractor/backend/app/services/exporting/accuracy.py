"""Pure accuracy / label helpers for GT export (no LLM I/O)."""

from __future__ import annotations

from typing import Any

from research.steps.attribute_grouping.domain.models import AttrType
from research.steps.extraction.eval.models import EvalRow

# Excel metrics sheet expects FP1/FP2 (legacy names); research eval uses FP_1/FP_2.
EXCEL_LABELS = {
    "TP": "TP",
    "TN": "TN",
    "FN": "FN",
    "FP_1": "FP1",
    "FP_2": "FP2",
}


def accuracy_surface(rows: list[EvalRow]) -> dict[str, Any]:
    total = len(rows)
    error_count = sum(1 for row in rows if row.extraction_error)
    hc_rows = [row for row in rows if row.confidence_label == "HC"]
    lc_rows = [row for row in rows if row.confidence_label == "LC"]
    hc_correct = sum(1 for row in hc_rows if row.is_match)
    lc_correct = sum(1 for row in lc_rows if row.is_match)
    return {
        "accuracy": case_accuracy(hc_correct + lc_correct, total),
        "n_cases": total,
        "error_count": error_count,
        "high_confidence": {
            "n": len(hc_rows),
            "accuracy": case_accuracy(hc_correct, len(hc_rows)),
        },
        "low_confidence": {
            "n": len(lc_rows),
            "accuracy": case_accuracy(lc_correct, len(lc_rows)),
        },
    }


def case_accuracy(n_correct: int, n_total: int) -> float | None:
    if n_total <= 0:
        return None
    return round(n_correct / n_total, 4)


def to_attr_type(value_type: str) -> AttrType:
    try:
        return AttrType(str(value_type).strip().lower())
    except ValueError:
        return AttrType.STRING


def excel_label(base_label: str) -> str:
    return EXCEL_LABELS.get(base_label, base_label)
