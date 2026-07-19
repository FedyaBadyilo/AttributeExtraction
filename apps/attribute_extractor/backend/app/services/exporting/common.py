from __future__ import annotations

from typing import Any

import pandas as pd

from backend.app.schemas import TzPackageRead


def total_value_columns(attrs) -> int:
    return 3 + sum(2 if attr.has_unit else 1 for attr in attrs)


def package_key(package: TzPackageRead) -> str:
    """Stable package id aligned with pipeline checkpoints and ``PipelineTzResult.package_id``."""
    return str(package.package_id or package.recpart or package.tz_id)


def package_recpart(package: TzPackageRead) -> str:
    return str(package.recpart or package.package_id or package.tz_id)


def confidence_label(value: bool | None) -> str | None:
    if value is True:
        return "high"
    if value is False:
        return "low"
    return None


def display(value: Any, *, missing_display: Any = "Н/Д") -> Any:
    if is_missing(value):
        return missing_display
    return value


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def cell_text(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()

