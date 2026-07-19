from __future__ import annotations

from collections import Counter, OrderedDict

from research.steps.extraction.eval.models import EvalRow

_CORRECT_LABELS = frozenset({"TP", "TN"})


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_metrics(rows: list[EvalRow]) -> dict[str, float]:
    count = len(rows)
    labels = Counter(row.base_label for row in rows)
    confidence = Counter(row.confidence_label for row in rows)
    errors = sum(1 for row in rows if row.extraction_error)
    correct = labels["TP"] + labels["TN"]
    hc_rows = [row for row in rows if row.confidence_label == "HC"]
    lc_rows = [row for row in rows if row.confidence_label == "LC"]
    hc_correct = sum(1 for row in hc_rows if row.base_label in _CORRECT_LABELS)
    lc_correct = sum(1 for row in lc_rows if row.base_label in _CORRECT_LABELS)

    metrics: "OrderedDict[str, float]" = OrderedDict()
    metrics["accuracy"] = _safe_rate(correct, count)
    metrics["count"] = float(count)
    metrics["errors"] = float(errors)
    metrics["hc_rate"] = _safe_rate(confidence["HC"], count)
    metrics["lc_rate"] = _safe_rate(confidence["LC"], count)
    metrics["hc_accuracy"] = _safe_rate(hc_correct, len(hc_rows))
    metrics["lc_accuracy"] = _safe_rate(lc_correct, len(lc_rows))
    metrics["tp_rate"] = _safe_rate(labels["TP"], count)
    metrics["tn_rate"] = _safe_rate(labels["TN"], count)
    metrics["fp1_rate"] = _safe_rate(labels["FP_1"], count)
    metrics["fp2_rate"] = _safe_rate(labels["FP_2"], count)
    metrics["fn_rate"] = _safe_rate(labels["FN"], count)
    metrics["tp_count"] = float(labels["TP"])
    metrics["tn_count"] = float(labels["TN"])
    metrics["fp1_count"] = float(labels["FP_1"])
    metrics["fp2_count"] = float(labels["FP_2"])
    metrics["fn_count"] = float(labels["FN"])
    return dict(metrics)
