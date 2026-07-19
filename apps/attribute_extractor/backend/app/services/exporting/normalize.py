"""Normalize ground-truth / prediction cell values by attribute type."""

from __future__ import annotations

from typing import Any

import pandas as pd

NULL_LIKE_STRINGS = {"-", "", "—", "–", "н.д.", "н/д", "n/a", "отсутствует"}


def is_null_like(value: Any) -> bool:
    if pd.isna(value):
        return True
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in NULL_LIKE_STRINGS:
        return True
    return False


def normalize_value(value: Any, value_type: str) -> Any:
    if is_null_like(value):
        return None
    if value == 0 or value == 0.0:
        return None
    if value_type == "number":
        try:
            text = str(value).strip().replace(",", ".")
            number = float(text)
            return int(number) if number == int(number) else number
        except (ValueError, TypeError):
            return value
    if value_type == "bool":
        text = str(value).strip().lower()
        if text in ("да", "yes", "true", "1"):
            return True
        if text in ("нет", "no", "false", "0"):
            return False
        return value
    if value_type in ("enum", "str", "string"):
        text = str(value).strip() if value is not None else None
        # Source Excel uses '|' as a multi-value separator meaning "или".
        if text and "|" in text:
            parts = [part.strip() for part in text.split("|")]
            filtered = [part for part in parts if part and not is_null_like(part)]
            if not filtered:
                return None
            text = " или ".join(filtered)
        return text
    return value
