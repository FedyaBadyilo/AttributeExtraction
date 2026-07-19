"""Excel result exporter for completed backend tasks."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from backend.app.pipeline.runner import PipelineTzResult
from backend.app.schemas import TaskRead, ValidationReport
from backend.app.services import file_cache
from backend.app.services.exporting import evaluation, ground_truth, manifest, metrics_sheet, results_sheet
from backend.app.services.exporting.config import SHEET_RESULTS
from backend.app.services.exporting.models import AttributeColumn, ExportMode


def write_result_workbook(
    *,
    task: TaskRead,
    report: ValidationReport,
    results: list[PipelineTzResult],
    attributes_set: Any,
    pipeline_version: str,
) -> Path:
    """Build and save task ``result.xlsx`` after processing has completed."""
    path = file_cache.result_path(task.id)
    path.parent.mkdir(parents=True, exist_ok=True)

    attrs = _attribute_columns(attributes_set)
    result_by_package = {result.package_id: result for result in results}
    mode = _export_mode(task)
    workbook = Workbook()
    generated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    _build_workbook_for_mode(
        workbook=workbook,
        mode=mode,
        task=task,
        report=report,
        result_by_package=result_by_package,
        attrs=attrs,
        pipeline_version=pipeline_version,
        generated_at=generated_at,
    )

    workbook.save(path)
    _write_result_manifest(task, pipeline_version=pipeline_version)
    return path


def result_manifest_matches(task: TaskRead, *, pipeline_version: str) -> bool:
    return manifest.result_manifest_matches(task, pipeline_version=pipeline_version)


def _write_result_manifest(task: TaskRead, *, pipeline_version: str) -> None:
    manifest.write_result_manifest(task, pipeline_version=pipeline_version)


def _export_mode(task: TaskRead) -> ExportMode:
    return "with_gt" if task.has_ground_truth else "predictions"


def _build_workbook_for_mode(
    *,
    workbook: Workbook,
    mode: ExportMode,
    task: TaskRead,
    report: ValidationReport,
    result_by_package: dict[str, PipelineTzResult],
    attrs: list[AttributeColumn],
    pipeline_version: str,
    generated_at: datetime,
) -> None:
    worksheet = workbook.active
    worksheet.title = SHEET_RESULTS

    if mode == "with_gt":
        gt_maps = _load_ground_truth_maps(task.id, report.packages, attrs)
        eval_payload = _evaluate_with_ground_truth(report.packages, result_by_package, attrs, gt_maps)
        layout = results_sheet.build_results_sheet(
            worksheet,
            packages=report.packages,
            result_by_package=result_by_package,
            attrs=attrs,
            gt_maps=gt_maps,
            evaluation=eval_payload,
        )
        results_sheet.set_defined_names(workbook, layout)
        metrics_sheet.build_metrics_sheet(
            workbook,
            layout=layout,
            pipeline_version=pipeline_version,
            generated_at=generated_at,
            sample_count=len(report.packages),
        )
        metrics_sheet.build_auto_metrics_sheet(workbook, eval_payload.metrics)
        return

    layout = results_sheet.build_results_sheet(
        worksheet,
        packages=report.packages,
        result_by_package=result_by_package,
        attrs=attrs,
        gt_maps=None,
        evaluation=None,
    )
    results_sheet.set_defined_names(workbook, layout)


def _attribute_columns(attributes_set: Any) -> list[AttributeColumn]:
    cols: list[AttributeColumn] = []
    for attr_id, item in attributes_set.attributes.items():
        cols.append(
            AttributeColumn(
                attr_id=str(attr_id),
                attr_name=str(item.attribute_name or attr_id),
                has_unit=bool(item.has_unit),
                for_extraction=bool(item.for_extraction),
                essential=bool(item.essential),
                exclude=not bool(item.for_extraction),
                hint_srch=_clean_text(item.rag_hint),
                hint_ext=_clean_text(item.extraction_hint),
                value_type=str(item.value_type or "string"),
                altnames=[str(name) for name in (item.altnames or [])],
            )
        )
    return cols


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# Compatibility hooks used in local tests via monkeypatch.
def _load_ground_truth_maps(*args, **kwargs):
    return ground_truth.load_ground_truth_maps(*args, **kwargs)


def _evaluate_with_ground_truth(*args, **kwargs):
    return evaluation.evaluate_with_ground_truth(*args, **kwargs)
