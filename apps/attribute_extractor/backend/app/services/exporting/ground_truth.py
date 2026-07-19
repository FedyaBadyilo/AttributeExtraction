from __future__ import annotations

from typing import Any

import pandas as pd

from backend.app.schemas import TzPackageRead
from backend.app.services import file_cache
from backend.app.services.excel_io import read_excel_sheets
from backend.app.services.exporting.common import cell_text, package_recpart
from backend.app.services.exporting.config import UNIT_SUFFIX
from backend.app.services.exporting.models import AttributeColumn
from backend.app.services.exporting.normalize import normalize_value as _normalize_value


def load_ground_truth_maps(
    task_id: str,
    packages: list[TzPackageRead],
    attrs: list[AttributeColumn],
) -> tuple[dict[tuple[str, str], Any], dict[tuple[str, str], str | None]]:
    expected_recparts = {package_recpart(package) for package in packages}
    extraction_attrs = [attr for attr in attrs if attr.for_extraction]
    attr_by_id = {attr.attr_id: attr for attr in extraction_attrs}
    attr_ids = set(attr_by_id)
    attr_ids_with_unit = {attr.attr_id for attr in extraction_attrs if attr.has_unit}
    if not attr_ids:
        return {}, {}

    path = file_cache.ground_truth_path(task_id)
    sheet_specs = discover_ground_truth_sheets(path, attr_ids, attr_ids_with_unit, expected_recparts)
    value_map: dict[tuple[str, str], Any] = {}
    unit_map: dict[tuple[str, str], str | None] = {}

    for recpart in expected_recparts:
        for spec in sheet_specs:
            row_idx = spec["recpart_rows"].get(recpart)
            if row_idx is None:
                continue
            frame = spec["frame"]
            for attr_id, col_idx in spec["attr_cols"].items():
                key = (recpart, attr_id)
                value = _normalize_value(frame.iat[row_idx, col_idx], attr_by_id[attr_id].value_type)
                value_map[key] = value
                unit_map[key] = gt_unit_value(frame, spec, row_idx, attr_id, value)
    return value_map, unit_map


def discover_ground_truth_sheets(
    path,
    attr_ids: set[str],
    attr_ids_with_unit: set[str],
    recparts: set[str],
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for sheet_name, frame in read_excel_sheets(path, header=None):
        discovered = find_code_row(frame, attr_ids)
        if discovered is None:
            continue
        code_row_idx, attr_cols, unit_cols = discovered
        recpart_rows = find_recpart_rows(frame, recparts, code_row_idx + 2)
        specs.append(
            {
                "sheet_name": sheet_name,
                "frame": frame,
                "attr_cols": attr_cols,
                "unit_cols": unit_cols,
                "code_row_idx": code_row_idx,
                "unit_row_idx": code_row_idx + 1,
                "recpart_rows": recpart_rows,
            }
        )

    if not specs:
        raise ValueError(f"Ground Truth contains no sheets with backend attribute codes: {path}")

    anchors = [spec for spec in specs if set(spec["recpart_rows"]) >= recparts]
    if not anchors:
        raise ValueError("Ground Truth contains no anchor sheet with all RECPart values")

    anchor = anchors[0]
    for spec in specs:
        if set(spec["recpart_rows"]) >= recparts:
            continue
        spec["recpart_rows"] = {
            recpart: anchor["recpart_rows"][recpart]
            for recpart in recparts
            if anchor["recpart_rows"][recpart] < len(spec["frame"].index)
        }

    missing_unit_cols = []
    for spec in specs:
        for attr_id in sorted(set(spec["attr_cols"]) & attr_ids_with_unit):
            if attr_id not in spec["unit_cols"]:
                missing_unit_cols.append(f"{attr_id} ({spec['sheet_name']})")
    if missing_unit_cols:
        raise ValueError(f"Ground Truth is missing unit columns: {missing_unit_cols}")

    return specs


def find_code_row(
    frame: pd.DataFrame,
    attr_ids: set[str],
) -> tuple[int, dict[str, int], dict[str, int]] | None:
    best: tuple[int, dict[str, int], dict[str, int]] | None = None
    for row_idx in range(len(frame.index)):
        attr_cols: dict[str, int] = {}
        unit_cols: dict[str, int] = {}
        for col_idx in range(len(frame.columns)):
            raw = cell_text(frame.iat[row_idx, col_idx])
            if raw.endswith(UNIT_SUFFIX):
                attr_id = raw[: -len(UNIT_SUFFIX)]
                if attr_id in attr_ids:
                    unit_cols[attr_id] = col_idx
                continue
            if raw in attr_ids:
                attr_cols[raw] = col_idx
        if attr_cols and (best is None or len(attr_cols) > len(best[1])):
            best = (row_idx, attr_cols, unit_cols)
    return best


def find_recpart_rows(
    frame: pd.DataFrame,
    recparts: set[str],
    data_start_row_idx: int,
) -> dict[str, int]:
    rows: dict[str, int] = {}
    for row_idx in range(data_start_row_idx, len(frame.index)):
        for col_idx in range(len(frame.columns)):
            value = cell_text(frame.iat[row_idx, col_idx])
            if value in recparts and value not in rows:
                rows[value] = row_idx
    return rows


def gt_unit_value(
    frame: pd.DataFrame,
    spec: dict[str, Any],
    row_idx: int,
    attr_id: str,
    value: Any,
) -> str | None:
    if value is None:
        return None
    unit_col = spec["unit_cols"].get(attr_id)
    unit_value = None
    if unit_col is not None:
        unit_value = _normalize_value(frame.iat[row_idx, unit_col], "string")
    if unit_value is None:
        attr_col = spec["attr_cols"][attr_id]
        unit_value = _normalize_value(frame.iat[spec["unit_row_idx"], attr_col], "string")
    return str(unit_value) if unit_value is not None else None

