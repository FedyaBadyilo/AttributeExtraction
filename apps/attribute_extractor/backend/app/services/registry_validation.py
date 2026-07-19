"""Registry and source document validation for backend tasks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from backend.app.schemas import TzPackageRead, ValidationIssue, ValidationReport
from backend.app.services import file_cache
from backend.app.services.excel_io import read_excel_sheets


COL_TZ_ID = "Номер документа в ИС ЕОНКОМ"
COL_FILENAME = "Имя файла с расширением"
COL_IDX = "Номер для обработки"
COL_RECPART = "RECPart"
COL_EXEC = "исполнение"

REQUIRED_CANONICAL = (COL_TZ_ID, COL_FILENAME, COL_IDX, COL_EXEC)


@dataclass(frozen=True)
class RegistryRow:
    row_number: int
    process_index: int
    row: pd.Series
    tz_id: str
    recpart: str | None
    execution_variant: str | None


@dataclass(frozen=True)
class RegistryPackageRows:
    tz_id: str
    execution_variant: str | None
    rows: list[RegistryRow]


def validate_task_sources(task_id: str) -> ValidationReport:
    issues: list[ValidationIssue] = []
    packages: list[TzPackageRead] = []

    registry_path = file_cache.registry_path(task_id)
    documents_root = file_cache.documents_dir(task_id)

    if not registry_path.is_file():
        issues.append(
            ValidationIssue(
                code="registry_missing",
                message="Реестр не загружен",
                field="registry",
            )
        )
    if not documents_root.is_dir():
        issues.append(
            ValidationIssue(
                code="documents_missing",
                message="PDF-документы не загружены",
                field="documents",
            )
        )
    if issues:
        return ValidationReport(is_valid=False, issues=issues, packages=packages)

    dataframe = _read_registry(registry_path, issues)
    if dataframe is None:
        return ValidationReport(is_valid=False, issues=issues, packages=packages)

    recpart_column_present = bool(dataframe.attrs.get("recpart_column_present"))
    groups = _group_registry_rows(dataframe, recpart_column_present, issues)
    registry_file_names: list[str] = []
    for group in sorted(groups, key=lambda item: (item.tz_id, item.execution_variant or "")):
        package = _validate_tz_group(group, documents_root, recpart_column_present, issues, registry_file_names)
        if package is not None:
            packages.append(package)

    _validate_unique_package_ids(packages, issues)
    _validate_extra_pdfs(documents_root, registry_file_names, issues)
    return ValidationReport(is_valid=not issues, issues=issues, packages=packages)


def _read_registry(registry_path: Path, issues: list[ValidationIssue]) -> pd.DataFrame | None:
    try:
        sheets = read_excel_sheets(registry_path)
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="registry_read_failed",
                message="Не удалось прочитать реестр",
                field="registry",
                details={"error": str(exc)},
            )
        )
        return None

    sheet_names = [sheet_name for sheet_name, _ in sheets]
    if len(sheets) != 1:
        issues.append(
            ValidationIssue(
                code="registry_sheet_count_invalid",
                message="В реестре должен быть ровно один лист",
                field="registry",
                details={"sheet_names": sheet_names},
            )
        )
        return None

    dataframe = sheets[0][1]
    fold = _casefold_map(list(dataframe.columns))
    missing: list[str] = []
    rename: dict[str, str] = {}
    for required in REQUIRED_CANONICAL:
        key = required.casefold()
        if key not in fold:
            missing.append(required)
        else:
            rename[fold[key]] = required

    recpart_column_present = COL_RECPART.casefold() in fold
    if recpart_column_present:
        rename[fold[COL_RECPART.casefold()]] = COL_RECPART

    if missing:
        issues.append(
            ValidationIssue(
                code="registry_columns_missing",
                message="В реестре отсутствуют обязательные колонки",
                field="registry",
                details={"missing": missing, "actual": [str(column) for column in dataframe.columns]},
            )
        )
        return None

    dataframe = dataframe.rename(columns=rename)
    dataframe.attrs["recpart_column_present"] = recpart_column_present
    if not recpart_column_present:
        dataframe[COL_RECPART] = None
    return dataframe
def _group_registry_rows(
    dataframe: pd.DataFrame,
    recpart_column_present: bool,
    issues: list[ValidationIssue],
) -> list[RegistryPackageRows]:
    rows_by_tz_id: dict[str, list[RegistryRow]] = {}
    for row_number, row in dataframe.iterrows():
        tz_id = _cell_str(row[COL_TZ_ID])
        if tz_id is None:
            continue

        try:
            index = _to_int_process_index(row[COL_IDX])
        except ValueError as exc:
            issues.append(
                ValidationIssue(
                    code="registry_process_index_invalid",
                    message=str(exc),
                    field=COL_IDX,
                    tz_id=tz_id,
                    details={"row": int(row_number) + 2},
                )
            )
            continue

        if index < 0:
            issues.append(
                ValidationIssue(
                    code="registry_process_index_negative",
                    message="Номер для обработки не может быть отрицательным",
                    field=COL_IDX,
                    tz_id=tz_id,
                    details={"row": int(row_number) + 2, "value": index},
                )
            )
            continue

        recpart = _cell_str(row[COL_RECPART])
        if recpart_column_present and recpart is None:
            issues.append(
                ValidationIssue(
                    code="registry_recpart_missing",
                    message="Если колонка RECPart есть в реестре, она должна быть заполнена во всех строках",
                    field=COL_RECPART,
                    tz_id=tz_id,
                    details={"row": int(row_number) + 2},
                )
            )

        parsed = RegistryRow(
            row_number=int(row_number) + 2,
            process_index=index,
            row=row,
            tz_id=tz_id,
            recpart=recpart,
            execution_variant=_cell_str(row[COL_EXEC]),
        )
        rows_by_tz_id.setdefault(tz_id, []).append(parsed)

    if not rows_by_tz_id:
        issues.append(
            ValidationIssue(
                code="registry_empty",
                message="В реестре нет строк с заполненным tz_id",
                field=COL_TZ_ID,
            )
        )
        return []

    groups: list[RegistryPackageRows] = []
    for tz_id, rows in rows_by_tz_id.items():
        groups.extend(_split_tz_rows_into_packages(tz_id, rows, issues))
    return groups


def _split_tz_rows_into_packages(
    tz_id: str,
    rows: list[RegistryRow],
    issues: list[ValidationIssue],
) -> list[RegistryPackageRows]:
    main_rows = [row for row in rows if row.process_index == 0]
    if len(main_rows) <= 1:
        execution_variant = main_rows[0].execution_variant if main_rows else None
        return [RegistryPackageRows(tz_id=tz_id, execution_variant=execution_variant, rows=rows)]

    main_execution_variants = {row.execution_variant for row in main_rows}
    grouped: dict[str | None, list[RegistryRow]] = {
        execution_variant: [] for execution_variant in main_execution_variants
    }
    for row in rows:
        if row.process_index == 0:
            grouped.setdefault(row.execution_variant, []).append(row)
            continue

        if row.execution_variant in grouped:
            grouped[row.execution_variant].append(row)
            continue

        issues.append(
            ValidationIssue(
                code="registry_execution_variant_missing",
                message="Для нескольких исполнений одного tz_id у строк дополнений должна быть заполнена колонка «исполнение»",
                field=COL_EXEC,
                tz_id=tz_id,
                details={"row": row.row_number, "value": row.execution_variant},
            )
        )

    return [
        RegistryPackageRows(tz_id=tz_id, execution_variant=execution_variant, rows=grouped_rows)
        for execution_variant, grouped_rows in grouped.items()
        if grouped_rows
    ]


def _validate_tz_group(
    group: RegistryPackageRows,
    documents_root: Path,
    recpart_column_present: bool,
    issues: list[ValidationIssue],
    registry_file_names: list[str],
) -> TzPackageRead | None:
    tz_id = group.tz_id
    sorted_items = sorted(group.rows, key=lambda item: item.process_index)
    indices = [item.process_index for item in sorted_items]
    if 0 not in indices:
        issues.append(
            ValidationIssue(
                code="registry_main_row_missing",
                message="Для tz_id нет строки с «Номер для обработки» = 0",
                tz_id=tz_id,
                field=COL_IDX,
            )
        )
        return None
    if indices.count(0) != 1:
        issues.append(
            ValidationIssue(
                code="registry_main_row_duplicate",
                message="Для tz_id должна быть ровно одна строка с «Номер для обработки» = 0",
                tz_id=tz_id,
                field=COL_IDX,
                details={"count": indices.count(0)},
            )
        )
        return None

    row_by_index = {item.process_index: item for item in sorted_items}
    supplement_indices = [index for index in indices if index > 0]
    if len(supplement_indices) != len(set(supplement_indices)):
        issues.append(
            ValidationIssue(
                code="registry_supplement_index_duplicate",
                message="Дублируются индексы дополнений",
                tz_id=tz_id,
                field=COL_IDX,
                details={"indices": supplement_indices},
            )
        )
        return None
    if supplement_indices:
        max_index = max(supplement_indices)
        expected = set(range(1, max_index + 1))
        if set(supplement_indices) != expected:
            issues.append(
                ValidationIssue(
                    code="registry_supplement_index_gap",
                    message="Индексы дополнений должны идти без пропусков",
                    tz_id=tz_id,
                    field=COL_IDX,
                    details={"expected": sorted(expected), "actual": sorted(supplement_indices)},
                )
            )
            return None

    main_file_name = _resolve_pdf(tz_id, documents_root, row_by_index[0].row[COL_FILENAME], issues)
    if main_file_name is None:
        return None
    registry_file_names.append(main_file_name)

    supplements_by_index: dict[int, str] = {}
    for index in sorted(supplement_indices):
        file_name = _resolve_pdf(tz_id, documents_root, row_by_index[index].row[COL_FILENAME], issues)
        if file_name is None:
            return None
        supplements_by_index[index] = file_name
        registry_file_names.append(file_name)

    package_file_names = [main_file_name, *supplements_by_index.values()]
    _validate_package_duplicate_file_names(tz_id, package_file_names, issues)

    expected_file_names = set(package_file_names)
    for file_name in sorted(expected_file_names):
        _validate_pdf_text_layer(tz_id, documents_root / file_name, issues)

    recpart, recpart_source = _package_recpart(tz_id, group, recpart_column_present, issues)
    if recpart is None:
        return None

    return TzPackageRead(
        package_id=recpart,
        tz_id=tz_id,
        main_file_name=main_file_name,
        supplements_by_index=supplements_by_index,
        recpart=recpart,
        recpart_source=recpart_source,
        execution_variant=group.execution_variant,
    )


def _package_recpart(
    tz_id: str,
    group: RegistryPackageRows,
    recpart_column_present: bool,
    issues: list[ValidationIssue],
) -> tuple[str | None, str]:
    if not recpart_column_present:
        return _synthetic_recpart(tz_id, group.execution_variant), "synthetic"

    recparts = {row.recpart for row in group.rows if row.recpart is not None}
    if len(recparts) == 1:
        return next(iter(recparts)), "file"

    issues.append(
        ValidationIssue(
            code="registry_recpart_inconsistent",
            message="Все строки одного пакета обработки должны иметь одинаковый RECPart",
            field=COL_RECPART,
            tz_id=tz_id,
            details={
                "execution_variant": group.execution_variant,
                "recparts": sorted(str(recpart) for recpart in recparts),
            },
        )
    )
    return None, "file"


def _synthetic_recpart(tz_id: str, execution_variant: str | None) -> str:
    source = f"{tz_id}|{execution_variant or ''}"
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12].upper()
    return f"SYN-RECPart-{digest}"


def _validate_unique_package_ids(
    packages: list[TzPackageRead],
    issues: list[ValidationIssue],
) -> None:
    seen: dict[str, TzPackageRead] = {}
    duplicates: list[str] = []
    for package in packages:
        if package.package_id is None:
            continue
        if package.package_id in seen:
            duplicates.append(package.package_id)
        else:
            seen[package.package_id] = package

    if duplicates:
        issues.append(
            ValidationIssue(
                code="registry_package_id_duplicate",
                message="RECPart должен быть уникален для пакетов обработки",
                field=COL_RECPART,
                details={"duplicates": sorted(set(duplicates))},
            )
        )


def _resolve_pdf(
    tz_id: str,
    documents_root: Path,
    raw_file_name: Any,
    issues: list[ValidationIssue],
) -> str | None:
    file_name = str(raw_file_name).strip()
    if not file_name or file_name.lower() == "nan":
        issues.append(
            ValidationIssue(
                code="document_file_missing",
                message="Пустое «Имя файла с расширением»",
                tz_id=tz_id,
                field=COL_FILENAME,
            )
        )
        return None

    if Path(file_name).suffix != ".pdf":
        issues.append(
            ValidationIssue(
                code="document_file_not_pdf",
                message="Файл из реестра должен быть PDF",
                tz_id=tz_id,
                file_name=file_name,
                field=COL_FILENAME,
            )
        )
        return None

    if not (documents_root / file_name).is_file():
        issues.append(
            ValidationIssue(
                code="document_file_missing",
                message=f"Нет файла {file_name!r} в каталоге документов",
                tz_id=tz_id,
                field=COL_FILENAME,
            )
        )
        return None

    return file_name


def _validate_extra_pdfs(
    documents_root: Path,
    expected_file_names: list[str],
    issues: list[ValidationIssue],
) -> None:
    if not documents_root.is_dir():
        issues.append(
            ValidationIssue(
                code="documents_missing",
                message="PDF-документы не загружены",
                field="documents",
            )
        )
        return
    expected = set(expected_file_names)
    extra = sorted(
        path.name
        for path in documents_root.iterdir()
        if path.is_file()
        and path.suffix == ".pdf"
        and path.name not in expected
    )
    if extra:
        issues.append(
            ValidationIssue(
                code="documents_extra_pdf",
                message="Каталог документов содержит PDF, которых нет в реестре",
                field="documents",
                details={"extra": extra},
            )
        )


def _validate_package_duplicate_file_names(
    tz_id: str,
    file_names: list[str],
    issues: list[ValidationIssue],
) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for file_name in file_names:
        if file_name in seen:
            duplicates.add(file_name)
            continue
        seen.add(file_name)
    if duplicates:
        issues.append(
            ValidationIssue(
                code="registry_file_name_duplicate",
                message="Имена файлов в одном пакете должны быть уникальны",
                field=COL_FILENAME,
                tz_id=tz_id,
                details={"duplicates": sorted(duplicates)},
            )
        )


def _validate_pdf_text_layer(tz_id: str, pdf_path: Path, issues: list[ValidationIssue]) -> None:
    try:
        from pypdf import PdfReader
    except ModuleNotFoundError:
        issues.append(
            ValidationIssue(
                code="pdf_text_layer_checker_unavailable",
                message="Не установлена зависимость pypdf для проверки текстового слоя PDF",
                tz_id=tz_id,
                file_name=pdf_path.name,
                field="documents",
            )
        )
        return

    try:
        reader = PdfReader(str(pdf_path))
        text = "".join((page.extract_text() or "") for page in reader.pages[:3])
    except Exception as exc:
        issues.append(
            ValidationIssue(
                code="pdf_read_failed",
                message="Не удалось прочитать PDF",
                tz_id=tz_id,
                file_name=pdf_path.name,
                field="documents",
                details={"error": str(exc)},
            )
        )
        return

    if not text.strip():
        issues.append(
            ValidationIssue(
                code="pdf_text_layer_missing",
                message="PDF не содержит текстовый слой",
                tz_id=tz_id,
                file_name=pdf_path.name,
                field="documents",
            )
        )


def _casefold_map(columns: list[Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for column in columns:
        key = str(column).strip().casefold()
        if key not in result:
            result[key] = str(column).strip()
    return result


def _to_int_process_index(value: Any) -> int:
    if pd.isna(value):
        raise ValueError("Пустой «Номер для обработки»")
    if isinstance(value, bool):
        raise ValueError(f"Некорректный «Номер для обработки»: {value!r}")
    if isinstance(value, (int, float)):
        index = int(value)
        if float(value) != float(index):
            raise ValueError(f"Некорректный «Номер для обработки» (не целое): {value!r}")
        return index

    raw = str(value).strip()
    if not raw:
        raise ValueError("Пустой «Номер для обработки»")
    index = int(float(raw))
    if float(raw) != float(index):
        raise ValueError(f"Некорректный «Номер для обработки» (не целое): {value!r}")
    return index


def _cell_str(value: Any) -> str | None:
    if pd.isna(value):
        return None
    raw = str(value).strip()
    return raw if raw else None
