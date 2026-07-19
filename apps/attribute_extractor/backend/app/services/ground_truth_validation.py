"""Ground Truth RECPart validation for task uploads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.schemas import ValidationIssue, ValidationReport
from backend.app.services.excel_io import read_excel_sheets


RECPART_FIELD = "ground_truth"
_RECPART_PATTERN = re.compile(r"^(RECPart-|SYN-RECPart-)", re.IGNORECASE)
_UNIT_SUFFIX = " ед.из."
_MAX_CODE_SCAN_ROWS = 80


@dataclass(frozen=True)
class _AttributeSpec:
    attr_id: str
    has_unit: bool


@dataclass(frozen=True)
class _GroundTruthSheetSpec:
    sheet_name: str
    grid: list[list[str | None]]
    attr_cols: dict[str, int]
    unit_cols: dict[str, int]
    recpart_rows: dict[str, int]
    name_row_idx: int
    code_row_idx: int
    unit_row_idx: int
    data_start_row_idx: int


def expected_recparts_from_report(report: ValidationReport) -> set[str]:
    return {
        str(package.recpart).strip()
        for package in report.packages
        if package.recpart is not None and str(package.recpart).strip()
    }


def validate_ground_truth_file(
    ground_truth_path: Path,
    expected_recparts: set[str],
    attributes_set: Any | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    sheets = _read_ground_truth_sheets(ground_truth_path, issues)
    if sheets is None:
        return issues

    attr_specs = _attribute_specs(attributes_set)
    if attr_specs:
        actual_recparts = _validate_attribute_sheets(sheets, expected_recparts, attr_specs, issues)
    else:
        actual_recparts = _extract_ground_truth_recparts_from_sheets(sheets, expected_recparts)
        if not actual_recparts:
            issues.append(
                ValidationIssue(
                    code="ground_truth_recpart_not_found",
                    message="В Ground Truth не найдены строки RECPart",
                    field=RECPART_FIELD,
                )
            )

    if issues:
        return issues

    extra = sorted(actual_recparts - expected_recparts)
    missing = sorted(expected_recparts - actual_recparts)
    if extra:
        issues.append(
            ValidationIssue(
                code="ground_truth_extra_recpart",
                message="Ground Truth содержит RECPart, которых нет в текущем реестре",
                field=RECPART_FIELD,
                details={"recparts": extra},
            )
        )
    if missing:
        issues.append(
            ValidationIssue(
                code="ground_truth_missing_recpart",
                message="Ground Truth не содержит RECPart из текущего реестра",
                field=RECPART_FIELD,
                details={"recparts": missing},
            )
        )
    return issues


def extract_ground_truth_recparts(
    ground_truth_path: Path,
    expected_recparts: set[str],
    issues: list[ValidationIssue] | None = None,
) -> set[str]:
    """Extract RECPart values using the raw_data_preprocess anchor-sheet idea.

    The legacy preprocessing code searches RECPart values in attribute sheets after
    the attribute-code row. Here we only need the set of rows, so we find columns
    that contain expected RECPart values or RECPart-like labels and collect values
    from those columns.
    """

    issues = issues if issues is not None else []
    sheets = _read_ground_truth_sheets(ground_truth_path, issues)
    if sheets is None:
        return set()

    recparts = _extract_ground_truth_recparts_from_sheets(sheets, expected_recparts)
    if not recparts:
        issues.append(
            ValidationIssue(
                code="ground_truth_recpart_not_found",
                message="В Ground Truth не найдены строки RECPart",
                field=RECPART_FIELD,
            )
        )
    return recparts


def _read_ground_truth_sheets(
    ground_truth_path: Path,
    issues: list[ValidationIssue],
) -> list[tuple[str, pd.DataFrame]] | None:
    try:
        return read_excel_sheets(ground_truth_path, header=None)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="ground_truth_read_failed",
                message="Не удалось прочитать Ground Truth",
                field=RECPART_FIELD,
                details={"error": str(exc)},
            )
        )
        return None


def _attribute_specs(attributes_set: Any | None) -> dict[str, _AttributeSpec]:
    if attributes_set is None:
        return {}
    specs: dict[str, _AttributeSpec] = {}
    for attr_id, item in getattr(attributes_set, "attributes", {}).items():
        if not bool(item.for_extraction):
            continue
        specs[str(attr_id)] = _AttributeSpec(attr_id=str(attr_id), has_unit=bool(item.has_unit))
    return specs


def _extract_ground_truth_recparts_from_sheets(
    sheets: list[tuple[str, pd.DataFrame]],
    expected_recparts: set[str],
) -> set[str]:
    recparts: set[str] = set()
    for _sheet_name, dataframe in sheets:
        recparts.update(_extract_sheet_recparts(dataframe, expected_recparts))
    return recparts


def _validate_attribute_sheets(
    sheets: list[tuple[str, pd.DataFrame]],
    expected_recparts: set[str],
    attr_specs: dict[str, _AttributeSpec],
    issues: list[ValidationIssue],
) -> set[str]:
    if not attr_specs:
        return _extract_ground_truth_recparts_from_sheets(sheets, expected_recparts)

    attr_ids = set(attr_specs)
    attr_ids_with_unit = {attr_id for attr_id, spec in attr_specs.items() if spec.has_unit}
    specs: list[_GroundTruthSheetSpec] = []
    code_sources: dict[str, str] = {}

    for sheet_name, frame in sheets:
        grid = _sheet_text_grid(frame)
        discovered = _find_code_row(grid, attr_ids, sheet_name, issues)
        if discovered is None:
            continue

        code_row_idx, attr_cols, unit_cols = discovered
        name_row_idx = code_row_idx - 1
        unit_row_idx = code_row_idx + 1
        data_start_row_idx = code_row_idx + 2

        if name_row_idx < 0:
            issues.append(_issue("ground_truth_code_row_first", f"Лист {sheet_name!r}: строка кодов атрибутов не может быть первой", sheet_name=sheet_name))
            continue
        if unit_row_idx >= len(grid):
            issues.append(_issue("ground_truth_units_row_missing", f"Лист {sheet_name!r}: после строки кодов атрибутов нет строки единиц", sheet_name=sheet_name))
            continue

        spec = _GroundTruthSheetSpec(
            sheet_name=sheet_name,
            grid=grid,
            attr_cols=attr_cols,
            unit_cols=unit_cols,
            recpart_rows=_find_recpart_rows(grid, expected_recparts, data_start_row_idx, sheet_name, issues),
            name_row_idx=name_row_idx,
            code_row_idx=code_row_idx,
            unit_row_idx=unit_row_idx,
            data_start_row_idx=data_start_row_idx,
        )
        _validate_header_rows(spec, issues)
        specs.append(spec)

        for attr_id, col_idx in attr_cols.items():
            source = f"{sheet_name!r}, строка {code_row_idx + 1}, колонка {col_idx + 1}"
            prev = code_sources.get(attr_id)
            if prev is not None:
                issues.append(
                    _issue(
                        "ground_truth_attribute_duplicate",
                        f"GT содержит атрибут {attr_id!r} в нескольких местах",
                        sheet_name=sheet_name,
                        details={"attribute_id": attr_id, "first": prev, "second": source},
                    )
                )
            else:
                code_sources[attr_id] = source

    if not specs:
        issues.append(
            _issue(
                "ground_truth_attribute_sheets_not_found",
                "В Ground Truth не найдены листы со строкой кодов атрибутов из справочника",
                details={"expected_examples": sorted(attr_ids)[:10]},
            )
        )
        return set()

    _validate_attribute_coverage(attr_ids, attr_ids_with_unit, specs, issues)
    _validate_anchor_alignment(specs, expected_recparts, issues)

    return _extract_ground_truth_recparts_from_sheets(sheets, expected_recparts)


def _sheet_text_grid(frame: pd.DataFrame) -> list[list[str | None]]:
    if frame.empty:
        return []
    values = frame.to_numpy(dtype=object, copy=False)
    return [[_cell_text(values[row_idx, col_idx]) for col_idx in range(values.shape[1])] for row_idx in range(values.shape[0])]


def _find_code_row(
    grid: list[list[str | None]],
    attr_ids: set[str],
    sheet_name: str,
    issues: list[ValidationIssue],
) -> tuple[int, dict[str, int], dict[str, int]] | None:
    best: tuple[int, dict[str, int], dict[str, int]] | None = None
    limit = min(len(grid), _MAX_CODE_SCAN_ROWS)
    for row_idx in range(limit):
        attr_cols: dict[str, int] = {}
        unit_cols: dict[str, int] = {}
        row = grid[row_idx]
        for col_idx, raw in enumerate(row):
            if raw is None:
                continue
            if raw.endswith(_UNIT_SUFFIX):
                attr_id = raw[: -len(_UNIT_SUFFIX)]
                if attr_id in attr_ids:
                    if attr_id in unit_cols:
                        issues.append(_duplicate_issue("ground_truth_unit_column_duplicate", sheet_name, row_idx, attr_id))
                    unit_cols[attr_id] = col_idx
                continue
            if raw in attr_ids:
                if raw in attr_cols:
                    issues.append(_duplicate_issue("ground_truth_attribute_column_duplicate", sheet_name, row_idx, raw))
                attr_cols[raw] = col_idx

        if attr_cols and (best is None or len(attr_cols) > len(best[1])):
            best = (row_idx, attr_cols, unit_cols)
    return best


def _find_recpart_rows(
    grid: list[list[str | None]],
    recparts: set[str],
    data_start_row_idx: int,
    sheet_name: str,
    issues: list[ValidationIssue],
) -> dict[str, int]:
    rows: dict[str, int] = {}
    remaining = set(recparts)
    for row_idx in range(data_start_row_idx, len(grid)):
        if not remaining:
            break
        for value in grid[row_idx]:
            if value not in remaining:
                continue
            if value in rows:
                issues.append(
                    _issue(
                        "ground_truth_recpart_duplicate_on_sheet",
                        f"Лист {sheet_name!r}: RECPart {value!r} найден более одного раза",
                        sheet_name=sheet_name,
                        details={"recpart": value, "rows": [rows[value] + 1, row_idx + 1]},
                    )
                )
            else:
                rows[value] = row_idx
                remaining.discard(value)
    return rows


def _validate_header_rows(spec: _GroundTruthSheetSpec, issues: list[ValidationIssue]) -> None:
    unit_row_label = spec.grid[spec.unit_row_idx][0] if spec.grid[spec.unit_row_idx] else None
    if unit_row_label != "Единицы измерения":
        issues.append(
            _issue(
                "ground_truth_units_row_invalid",
                f"Лист {spec.sheet_name!r}: сразу после строки кодов должна быть строка 'Единицы измерения'",
                sheet_name=spec.sheet_name,
                details={"row": spec.unit_row_idx + 1, "column": 1, "value": unit_row_label},
            )
        )
    for attr_id, col_idx in spec.attr_cols.items():
        name_row = spec.grid[spec.name_row_idx]
        name = name_row[col_idx] if col_idx < len(name_row) else None
        if not name:
            issues.append(
                _issue(
                    "ground_truth_attribute_name_missing",
                    f"Лист {spec.sheet_name!r}: пустое имя атрибута {attr_id!r} над строкой кодов",
                    sheet_name=spec.sheet_name,
                    details={"attribute_id": attr_id, "row": spec.name_row_idx + 1, "column": col_idx + 1},
                )
            )


def _validate_attribute_coverage(
    attr_ids: set[str],
    attr_ids_with_unit: set[str],
    specs: list[_GroundTruthSheetSpec],
    issues: list[ValidationIssue],
) -> None:
    found_attr_ids = {attr_id for spec in specs for attr_id in spec.attr_cols}
    missing_attrs = sorted(attr_ids - found_attr_ids)
    if missing_attrs:
        issues.append(
            _issue(
                "ground_truth_attributes_missing",
                "В Ground Truth отсутствуют атрибуты из справочника",
                details={"attribute_ids": missing_attrs},
            )
        )

    unexpected_unit_cols: list[str] = []
    missing_unit_cols: list[str] = []
    for spec in specs:
        for attr_id in sorted(set(spec.unit_cols) - attr_ids_with_unit):
            unexpected_unit_cols.append(f"{attr_id} ({spec.sheet_name}, строка {spec.code_row_idx + 1})")
        for attr_id in sorted(set(spec.attr_cols) & attr_ids_with_unit):
            if attr_id not in spec.unit_cols:
                missing_unit_cols.append(f"{attr_id} ({spec.sheet_name}, строка {spec.code_row_idx + 1})")

    if unexpected_unit_cols:
        issues.append(
            _issue(
                "ground_truth_unexpected_unit_columns",
                "В Ground Truth есть unit-колонки для атрибутов без единиц измерения в справочнике",
                details={"columns": unexpected_unit_cols},
            )
        )
    if missing_unit_cols:
        issues.append(
            _issue(
                "ground_truth_unit_columns_missing",
                "В Ground Truth отсутствуют unit-колонки для атрибутов с единицами измерения",
                details={"columns": missing_unit_cols},
            )
        )


def _validate_anchor_alignment(
    specs: list[_GroundTruthSheetSpec],
    recparts: set[str],
    issues: list[ValidationIssue],
) -> None:
    anchor_specs = [spec for spec in specs if spec.recpart_rows]
    for spec in anchor_specs:
        missing = sorted(recparts - set(spec.recpart_rows))
        if missing:
            issues.append(
                _issue(
                    "ground_truth_recpart_rows_missing_on_sheet",
                    f"Лист {spec.sheet_name!r}: не найдены строки для RECPart из текущего реестра",
                    sheet_name=spec.sheet_name,
                    details={"recparts": missing},
                )
            )

    anchors_with_all_rows = [spec for spec in anchor_specs if set(spec.recpart_rows) >= recparts]
    if not anchors_with_all_rows:
        issues.append(
            _issue(
                "ground_truth_anchor_sheet_missing",
                "В Ground Truth нет anchor-листа со всеми RECPart из текущего реестра",
                details={"recparts": sorted(recparts)},
            )
        )
        return

    anchor = anchors_with_all_rows[0]
    for spec in specs:
        if spec.recpart_rows:
            continue
        for recpart in recparts:
            anchor_row = anchor.recpart_rows[recpart]
            if anchor_row >= len(spec.grid):
                issues.append(
                    _issue(
                        "ground_truth_sheet_not_aligned",
                        f"Лист {spec.sheet_name!r}: нет строки {anchor_row + 1} для RECPart {recpart!r}",
                        sheet_name=spec.sheet_name,
                        details={"recpart": recpart, "anchor_sheet": anchor.sheet_name, "row": anchor_row + 1},
                    )
                )
                continue
            expected = anchor.grid[anchor_row][0] if anchor.grid[anchor_row] else None
            actual = spec.grid[anchor_row][0] if spec.grid[anchor_row] else None
            if actual != expected:
                issues.append(
                    _issue(
                        "ground_truth_sheet_not_aligned",
                        f"Лист {spec.sheet_name!r}: строка {anchor_row + 1} не выровнена с anchor-листом",
                        sheet_name=spec.sheet_name,
                        details={
                            "recpart": recpart,
                            "anchor_sheet": anchor.sheet_name,
                            "row": anchor_row + 1,
                            "expected": expected,
                            "actual": actual,
                        },
                    )
                )


def _duplicate_issue(code: str, sheet_name: str, row_idx: int, attr_id: str) -> ValidationIssue:
    return _issue(
        code,
        f"Лист {sheet_name!r}: атрибут {attr_id!r} дублируется в строке кодов",
        sheet_name=sheet_name,
        details={"attribute_id": attr_id, "row": row_idx + 1},
    )


def _issue(
    code: str,
    message: str,
    *,
    sheet_name: str | None = None,
    details: dict[str, Any] | None = None,
) -> ValidationIssue:
    payload = dict(details or {})
    if sheet_name is not None:
        payload.setdefault("sheet_name", sheet_name)
    return ValidationIssue(code=code, message=message, field=RECPART_FIELD, details=payload)


def _extract_sheet_recparts(
    dataframe: pd.DataFrame,
    expected_recparts: set[str],
) -> set[str]:
    grid = _sheet_text_grid(dataframe)
    return _extract_sheet_recparts_from_grid(grid, expected_recparts)


def _extract_sheet_recparts_from_grid(
    grid: list[list[str | None]],
    expected_recparts: set[str],
) -> set[str]:
    values: set[str] = set()
    if not grid:
        return values

    data_start_row = _guess_data_start_row(grid)
    candidate_columns = _candidate_recpart_columns(grid, data_start_row, expected_recparts)
    for column in candidate_columns:
        for row in grid[data_start_row:]:
            if column >= len(row):
                continue
            value = row[column]
            if value is None or value == "0":
                continue
            if value in expected_recparts or _looks_like_recpart(value):
                values.add(value)
    return values


def _candidate_recpart_columns(
    grid: list[list[str | None]],
    data_start_row: int,
    expected_recparts: set[str],
) -> set[int]:
    columns: set[int] = set()
    for row in grid[data_start_row:]:
        for column, value in enumerate(row):
            if value is None:
                continue
            if value in expected_recparts or _looks_like_recpart(value):
                columns.add(column)
    return columns


def _guess_data_start_row(grid: list[list[str | None]]) -> int:
    for row_index, row in enumerate(grid):
        if any(value == "Единицы измерения" for value in row):
            return row_index + 1
    return 0


def _looks_like_recpart(value: str) -> bool:
    return bool(_RECPART_PATTERN.match(value))


def _cell_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None
