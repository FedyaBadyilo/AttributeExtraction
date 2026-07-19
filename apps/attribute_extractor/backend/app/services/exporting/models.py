from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class AttributeColumn:
    attr_id: str
    attr_name: str
    has_unit: bool
    for_extraction: bool
    essential: bool
    exclude: bool
    hint_srch: str | None
    hint_ext: str | None
    value_type: str
    altnames: list[str]


@dataclass(frozen=True)
class ExportEvaluation:
    labels_by_recpart: dict[str, dict[str, str]]
    metrics: dict[str, Any]


@dataclass(frozen=True)
class BlockLayout:
    title_row: int
    first_data_row: int
    last_data_row: int


@dataclass(frozen=True)
class ResultsLayout:
    first_attr_col: int
    last_col: int
    header_row: int
    attr_code_row: int
    essential_row: int
    exclude_row: int
    gt_first_row: int | None
    gt_last_row: int | None
    pred_first_row: int
    pred_last_row: int
    source_first_row: int
    source_last_row: int
    labels_first_row: int | None
    labels_last_row: int | None
    confidence_first_row: int
    confidence_last_row: int


ExportMode = Literal["with_gt", "predictions"]

