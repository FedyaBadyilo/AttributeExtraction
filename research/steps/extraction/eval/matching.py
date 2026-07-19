from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

from research.steps.attribute_grouping.domain.models import AttrType
from research.steps.extraction.eval.models import (
    BaseLabel,
    ConfidenceLabel,
    MatchResult,
)

_WS_RE = re.compile(r"\s+")
_CARET_POWER_RE = re.compile(r"\^(\d+)")
_SUPERSCRIPT_POWER_RE = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹]+")
_TEMP_UNIT_RE = re.compile(r"^(?:°|⁰|˚)?\s*[cс]$")
_SUPERSCRIPT_TO_DIGIT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")

# Canonical forms for high-frequency equivalent spellings (E006 mass cases).
_UNIT_CANONICAL: dict[str, str] = {
    "мес": "месяц",
    "месяц": "месяц",
    "ph": "ph",
    "ед. ph": "ph",
    "ед ph": "ph",
}


def confidence_label(high_confidence: bool | None) -> ConfidenceLabel:
    return "HC" if high_confidence is True else "LC"


def label_for_case(gt_value: Any, pred_value: Any, is_match: bool) -> BaseLabel:
    if gt_value is None and pred_value is None:
        return "TN"
    if gt_value is None and pred_value is not None:
        return "FP_1"
    if gt_value is not None and pred_value is None:
        return "FN"
    return "TP" if is_match else "FP_2"


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _normalize_string(value: str) -> str:
    return _WS_RE.sub(" ", value.replace("\u00a0", " ")).strip()


def needs_string_judge(*, gt_value: Any, pred_value: Any, attr_type: AttrType) -> bool:
    if gt_value is None or pred_value is None:
        return False
    if attr_type in (
        AttrType.NUMBER,
        AttrType.RANGE,
        AttrType.ENUM,
        AttrType.ENUM_LIST,
        AttrType.BOOL,
    ):
        return False
    deterministic_match, _ = _matches_string_deterministic(str(gt_value), str(pred_value))
    return not deterministic_match


def _matches_string_deterministic(gt_value: str, pred_value: str) -> tuple[bool, str]:
    gt_text = _normalize_string(gt_value)
    pred_text = _normalize_string(pred_value)
    if gt_text.casefold() == pred_text.casefold():
        return True, "string_casefold_exact"

    distance = _edit_distance(gt_text, pred_text)
    tolerance = max(1, len(gt_text) // 5)
    if distance <= tolerance:
        return True, "string_edit_distance"
    return False, "string_needs_judge"


def _matches_number(gt_value: Any, pred_value: Any) -> bool:
    return math.isclose(float(gt_value), float(pred_value), rel_tol=0.0, abs_tol=0.0)


def _matches_range(gt_value: list[float], pred_value: list[float]) -> bool:
    return (
        math.isclose(gt_value[0], pred_value[0], rel_tol=0.0, abs_tol=0.0)
        and math.isclose(gt_value[1], pred_value[1], rel_tol=0.0, abs_tol=0.0)
    )


def _matches_enum_list(gt_value: Any, pred_value: Any) -> bool:
    if isinstance(gt_value, list):
        gt_items = gt_value
    else:
        gt_items = [gt_value]
    if not isinstance(pred_value, list):
        pred_items = [pred_value]
    else:
        pred_items = pred_value
    return {str(item) for item in gt_items} == {str(item) for item in pred_items}


def _powers_to_caret(text: str) -> str:
    text = _CARET_POWER_RE.sub(r"^\1", text)
    return _SUPERSCRIPT_POWER_RE.sub(
        lambda match: "^" + match.group(0).translate(_SUPERSCRIPT_TO_DIGIT),
        text,
    )


def normalize_unit(unit: str) -> str:
    """Deterministic unit normalization for eval matching (mass E006-style cases)."""
    # NFC (not NFKC): compatibility decomposition would flatten ³→3 and ⁰→0.
    text = unicodedata.normalize("NFC", _normalize_string(unit))
    text = text.replace("\u2103", "°C").replace("\u2109", "°F")
    text = text.casefold()
    text = _WS_RE.sub(" ", text).strip()
    # Temperature forms before caret conversion so ⁰C stays recognizable.
    if _TEMP_UNIT_RE.fullmatch(text):
        return "°c"
    text = _powers_to_caret(text)
    return _UNIT_CANONICAL.get(text, text)


def _matches_unit_deterministic(
    gt_unit: str | None,
    pred_unit: str | None,
) -> tuple[bool, str]:
    if gt_unit is None or pred_unit is None:
        return False, "unit_mismatch"
    gt_norm = normalize_unit(gt_unit)
    pred_norm = normalize_unit(pred_unit)
    if gt_norm == pred_norm:
        if _normalize_string(gt_unit).casefold() == _normalize_string(pred_unit).casefold():
            return True, "unit_casefold_exact"
        return True, "unit_normalized"
    return False, "unit_needs_judge"


def needs_unit_judge(
    *,
    gt_value: Any,
    pred_value: Any,
    gt_unit: str | None,
    pred_unit: str | None,
    has_unit: bool,
    unit_matching_enabled: bool,
) -> bool:
    if not unit_matching_enabled or not has_unit:
        return False
    if gt_value is None or pred_value is None:
        return False
    if gt_unit is None or pred_unit is None:
        return False
    matched, _ = _matches_unit_deterministic(gt_unit, pred_unit)
    return not matched


def _with_unit_match(
    *,
    value_match: bool,
    match_method: str,
    apply_unit_matching: bool,
    gt_unit: str | None,
    pred_unit: str | None,
    string_judge_used: bool = False,
    unit_judge_verdict: bool | None = None,
) -> MatchResult:
    if not apply_unit_matching:
        return MatchResult(
            value_match=value_match,
            is_match=value_match,
            match_method=match_method,
            string_judge_used=string_judge_used,
        )

    unit_match, unit_match_method = _matches_unit_deterministic(gt_unit, pred_unit)
    unit_judge_used = False
    if not unit_match and unit_judge_verdict is not None:
        unit_match = unit_judge_verdict
        unit_match_method = "unit_llm_judge"
        unit_judge_used = True
    elif not unit_match:
        unit_match_method = "unit_mismatch" if unit_match_method == "unit_needs_judge" else unit_match_method

    return MatchResult(
        value_match=value_match,
        unit_match=unit_match,
        is_match=value_match and unit_match,
        match_method=match_method,
        unit_match_method=unit_match_method,
        string_judge_used=string_judge_used,
        unit_judge_used=unit_judge_used,
    )


def match_values(
    *,
    gt_value: Any,
    pred_value: Any,
    attr_type: AttrType,
    string_judge_verdict: bool | None = None,
    unit_judge_verdict: bool | None = None,
    gt_unit: str | None = None,
    pred_unit: str | None = None,
    unit_matching_enabled: bool = False,
    has_unit: bool = False,
) -> MatchResult:
    apply_unit_matching = unit_matching_enabled and has_unit

    if gt_value is None and pred_value is None:
        return MatchResult(value_match=True, is_match=True, match_method="both_null")
    if gt_value is None or pred_value is None:
        return MatchResult(value_match=False, is_match=False, match_method="one_null")

    if apply_unit_matching and gt_unit is None:
        raise ValueError(
            "unit_matching_enabled requires a non-null gt_unit when value is non-null "
            "for an attribute with units"
        )

    unit_kwargs = {
        "apply_unit_matching": apply_unit_matching,
        "gt_unit": gt_unit,
        "pred_unit": pred_unit,
        "unit_judge_verdict": unit_judge_verdict,
    }

    if attr_type == AttrType.NUMBER:
        return _with_unit_match(
            value_match=_matches_number(gt_value, pred_value),
            match_method="number_exact",
            **unit_kwargs,
        )

    if attr_type == AttrType.RANGE:
        return _with_unit_match(
            value_match=_matches_range(gt_value, pred_value),
            match_method="range_exact",
            **unit_kwargs,
        )

    if attr_type == AttrType.ENUM:
        return _with_unit_match(
            value_match=str(gt_value) == str(pred_value),
            match_method="enum_exact",
            **unit_kwargs,
        )

    if attr_type == AttrType.ENUM_LIST:
        return _with_unit_match(
            value_match=_matches_enum_list(gt_value, pred_value),
            match_method="enum_list_set",
            **unit_kwargs,
        )

    if attr_type == AttrType.BOOL:
        return _with_unit_match(
            value_match=gt_value == pred_value,
            match_method="bool_exact",
            **unit_kwargs,
        )

    deterministic_match, method = _matches_string_deterministic(str(gt_value), str(pred_value))
    if deterministic_match:
        return _with_unit_match(
            value_match=True,
            match_method=method,
            **unit_kwargs,
        )

    if string_judge_verdict is not None:
        return _with_unit_match(
            value_match=string_judge_verdict,
            match_method="string_llm_judge",
            string_judge_used=True,
            **unit_kwargs,
        )

    return _with_unit_match(
        value_match=False,
        match_method=method,
        **unit_kwargs,
    )
