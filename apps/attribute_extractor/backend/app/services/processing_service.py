"""Task processing orchestration service."""

from __future__ import annotations

import json
import logging
import re
import traceback
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.constants import PIPELINE_VERSION
from backend.app.errors import ApiError
from backend.app.pipeline.runner import PipelineTzResult, load_tz_pipeline_result, run_tz_pipeline
from backend.app.schemas import ProcessRestartMode, TaskRead, ValidationReport
from backend.app.services import export_service, file_cache, ground_truth_validation, reference_data, task_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProcessingPlan:
    task: TaskRead
    mode: ProcessRestartMode
    start_index: int
    checkpoint_results: list[PipelineTzResult]


@dataclass(frozen=True)
class ResultDownload:
    path: Path
    filename: str


def enqueue_processing(task_id: str, mode: ProcessRestartMode = "from_start") -> ProcessingPlan:
    task = task_service.get_task_by_id(task_id)
    report = _load_validation_report(task)
    if not report.is_valid or not report.packages:
        task_service.finish_processing_error(task_id, "Сначала исправьте ошибки в комплекте файлов")
        raise ApiError(
            status_code=409,
            code="task_validation_not_valid",
            message="Сначала исправьте ошибки в комплекте файлов",
        )
    attributes_set = reference_data.load_attributes_set(task.object_type)
    _validate_ground_truth_before_processing(task, report, attributes_set)

    start_index = 1
    checkpoint_results: list[PipelineTzResult] = []
    if mode == "from_failed_tz":
        start_index, checkpoint_results = _prepare_failed_tz_restart(task, report)

    task = task_service.start_processing(task_id, progress_tz_total=len(report.packages))
    _prepare_processing_files(task_id, mode=mode, keep_checkpoints=mode == "from_failed_tz")
    return ProcessingPlan(
        task=task,
        mode=mode,
        start_index=start_index,
        checkpoint_results=checkpoint_results,
    )


def _validate_ground_truth_before_processing(task: TaskRead, report: ValidationReport, attributes_set: Any) -> None:
    if not task.has_ground_truth:
        return

    ground_truth_path = file_cache.ground_truth_path(task.id)
    if not ground_truth_path.is_file():
        raise ApiError(
            status_code=409,
            code="ground_truth_missing",
            message="Файл эталонных данных не найден",
        )

    expected_recparts = ground_truth_validation.expected_recparts_from_report(report)
    issues = ground_truth_validation.validate_ground_truth_file(ground_truth_path, expected_recparts, attributes_set)
    if issues:
        raise ApiError(
            status_code=409,
            code="ground_truth_not_valid",
            message="Эталонные данные не соответствуют текущему комплекту",
            details=[issue.model_dump() for issue in issues],
        )


def process_task(task_id: str, plan: ProcessingPlan) -> None:
    log_path = file_cache.processing_log_path(task_id)
    current_tz_id: str | None = None
    current_tz_index: int | None = None
    current_execution_variant: str | None = None
    try:
        task = task_service.get_task_by_id(task_id)
        report = _load_validation_report(task)
        if not report.is_valid or not report.packages:
            raise RuntimeError("Сначала исправьте ошибки в комплекте файлов")

        _append_log(log_path, "Loading pipeline config and reference data")
        config = _load_pipeline_config()
        attr_set = reference_data.load_pipeline_attr_set(task.object_type)
        semantic_groups = reference_data.load_pipeline_attr_groups(task.object_type)

        results: list[PipelineTzResult] = list(plan.checkpoint_results)
        total = len(report.packages)
        for index, package in enumerate(report.packages, start=1):
            if index < plan.start_index:
                continue
            current_tz_id = package.tz_id
            current_tz_index = index
            current_execution_variant = package.execution_variant
            package_id = package.package_id or package.recpart or package.tz_id
            _append_log(log_path, f"Processing {package_id} / {package.tz_id} ({index}/{len(report.packages)})")
            task_service.set_processing_progress(
                task_id,
                "validate_input",
                f"Подготовка пакета {package.tz_id}",
                progress_tz_id=package.tz_id,
                progress_tz_index=index,
                progress_tz_total=total,
                progress_execution_variant=package.execution_variant,
            )
            result = run_tz_pipeline(
                task_id=task_id,
                package=package,
                config=config,
                attr_set=attr_set,
                semantic_groups=semantic_groups,
                progress_callback=lambda step, message, tz_id=package.tz_id, tz_index=index, execution_variant=package.execution_variant: _set_progress(
                    task_id,
                    log_path,
                    step,
                    message,
                    progress_tz_id=tz_id,
                    progress_tz_index=tz_index,
                    progress_tz_total=total,
                    progress_execution_variant=execution_variant,
                ),
            )
            results.append(result)
            _save_checkpoint(task_id, index, result)
            _append_log(log_path, f"Finished {result.package_id}: {result.output_path}")

        task_service.set_processing_progress(
            task_id,
            "done",
            "Обработка завершена",
            progress_tz_index=total,
            progress_tz_total=total,
            clear_progress_tz_id=True,
        )
        _append_log(log_path, "Processing completed; result.xlsx will be built on download")
        task_service.finish_processing_success(task_id, file_cache.RESULT_FILE_NAME)
    except Exception as exc:
        logger.exception("Task processing failed: %s", task_id)
        _write_error(task_id, exc)
        _append_log(file_cache.processing_log_path(task_id), f"ERROR: {exc}")
        task_service.finish_processing_error(
            task_id,
            str(exc),
            failed_tz_id=current_tz_id,
            failed_tz_index=current_tz_index,
            failed_execution_variant=current_execution_variant,
        )


def result_file_path(task_id: str) -> Path:
    return result_download(task_id).path


def result_download(task_id: str) -> ResultDownload:
    task = task_service.get_task_by_id(task_id)
    if task.status != "done":
        raise ApiError(
            status_code=409,
            code="task_result_not_ready",
            message="Результат еще не готов",
            details=[{"field": "status", "value": task.status}],
        )
    path = file_cache.result_path(task_id)
    has_ground_truth_for_export = task.has_ground_truth
    pipeline_version = _pipeline_version_from_checkpoints(task.id)
    if path.is_file() and not export_service.result_manifest_matches(task, pipeline_version=pipeline_version):
        file_cache.delete_result(task_id)
        path = file_cache.result_path(task_id)
    if not path.is_file():
        path, has_ground_truth_for_export = _build_result_file(task)
    return ResultDownload(
        path=path,
        filename=_result_download_filename(task, has_ground_truth=has_ground_truth_for_export),
    )


def _result_download_filename(task: TaskRead, *, has_ground_truth: bool | None = None) -> str:
    with_ground_truth = task.has_ground_truth if has_ground_truth is None else has_ground_truth
    object_type = _safe_filename_part(task_service.get_object_type_title(task.object_type), max_length=50)
    if not object_type:
        object_type = _safe_filename_part(task.object_type, max_length=50) or "тип"
    task_name = _safe_filename_part(task.name, max_length=50) or "задача"
    if with_ground_truth:
        return f"{object_type}_{task_name}_отчет_с_метриками.xlsx"
    return f"{object_type}_{task_name}_отчет.xlsx"


def _safe_filename_part(value: str, *, max_length: int = 80) -> str:
    normalized = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", value.strip())
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("._ ")
    return normalized[:max_length]


def _build_result_file(task: TaskRead) -> tuple[Path, bool]:
    report = _load_validation_report(task)
    results = _load_completed_results(task, report)
    pipeline_version = _pipeline_version_from_checkpoints(task.id)
    attributes_set = reference_data.load_attributes_set(task.object_type)
    if task.has_ground_truth and not file_cache.ground_truth_path(task.id).is_file():
        raise ApiError(
            status_code=409,
            code="ground_truth_missing",
            message="Файл эталонных данных не найден. Загрузите эталон заново.",
        )
    try:
        path = export_service.write_result_workbook(
            task=task,
            report=report,
            results=results,
            attributes_set=attributes_set,
            pipeline_version=pipeline_version,
        )
        return path, task.has_ground_truth
    except ApiError:
        raise
    except Exception as exc:
        raise ApiError(
            status_code=500,
            code="task_result_export_failed",
            message="Не удалось сформировать отчет",
            details=[{"field": "error", "value": str(exc)}],
        ) from exc


def _load_completed_results(task: TaskRead, report: ValidationReport) -> list[PipelineTzResult]:
    checkpoints = _load_checkpoints(task.id)
    results: list[PipelineTzResult] = []
    missing_indices: list[int] = []
    for index, package in enumerate(report.packages, start=1):
        item = checkpoints.get(str(index))
        if not item:
            missing_indices.append(index)
            continue
        result_path = file_cache.task_workspace(task.id) / str(item["output_path"])
        if not result_path.is_file():
            missing_indices.append(index)
            continue
        results.append(
            load_tz_pipeline_result(
                package_id=str(item["package_id"]),
                tz_id=str(item["tz_id"]),
                collection_name=str(item["collection_name"]),
                output_path=result_path,
            )
        )
    if missing_indices:
        raise ApiError(
            status_code=409,
            code="task_result_checkpoints_missing",
            message="Не найдены промежуточные результаты обработки",
            details=[{"field": "checkpoint_indices", "value": missing_indices}],
        )
    return results


def _load_validation_report(task: TaskRead) -> ValidationReport:
    if not task.last_validation:
        raise ApiError(
            status_code=409,
            code="task_validation_missing",
            message="Перед обработкой нужно проверить комплект файлов",
        )
    try:
        return ValidationReport.model_validate_json(task.last_validation)
    except ValueError as exc:
        raise ApiError(
            status_code=409,
            code="task_validation_corrupted",
            message="Отчет проверки поврежден. Запустите проверку комплекта заново",
        ) from exc


def _prepare_processing_files(
    task_id: str,
    *,
    mode: ProcessRestartMode,
    keep_checkpoints: bool,
) -> None:
    file_cache.ensure_workspace(task_id)
    log_path = file_cache.processing_log_path(task_id)
    error_path = file_cache.processing_error_path(task_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    error_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("", encoding="utf-8")
    error_path.unlink(missing_ok=True)
    file_cache.result_path(task_id).unlink(missing_ok=True)
    if mode == "from_start":
        _clear_checkpoint_outputs(task_id)
    elif not keep_checkpoints:
        file_cache.checkpoints_path(task_id).unlink(missing_ok=True)


def _prepare_failed_tz_restart(
    task: TaskRead,
    report: ValidationReport,
) -> tuple[int, list[PipelineTzResult]]:
    if task.status != "error":
        raise ApiError(
            status_code=409,
            code="restart_from_failed_tz_unavailable",
            message="Продолжить с места ошибки можно только для задач с ошибкой",
            details=[{"field": "status", "value": task.status}],
        )
    if not task.failed_tz_id or not task.failed_tz_index:
        raise ApiError(
            status_code=409,
            code="restart_failed_tz_missing",
            message="Не удалось определить место остановки. Запустите обработку с начала",
        )
    if task.failed_tz_index < 1 or task.failed_tz_index > len(report.packages):
        raise ApiError(
            status_code=409,
            code="restart_failed_tz_out_of_range",
            message="Место остановки не совпадает с текущим комплектом файлов",
            details=[
                {"field": "failed_tz_index", "value": task.failed_tz_index},
                {"field": "packages", "value": len(report.packages)},
            ],
        )
    failed_package = report.packages[task.failed_tz_index - 1]
    if failed_package.tz_id != task.failed_tz_id:
        raise ApiError(
            status_code=409,
            code="restart_inputs_changed_after_failure",
            message="После ошибки исходные файлы изменились. Запустите обработку с начала",
            details=[
                {"field": "failed_tz_id", "value": task.failed_tz_id},
                {"field": "current_tz_id", "value": failed_package.tz_id},
            ],
        )

    payload = _load_checkpoints_payload(task.id)
    checkpoint_pipeline_version = _pipeline_version_from_payload(payload)
    if checkpoint_pipeline_version != PIPELINE_VERSION:
        raise ApiError(
            status_code=409,
            code="restart_pipeline_version_mismatch",
            message="Продолжение с места ошибки недоступно: изменилась версия пайплайна. Запустите обработку с начала",
            details=[
                {"field": "checkpoint_pipeline_version", "value": checkpoint_pipeline_version},
                {"field": "current_pipeline_version", "value": PIPELINE_VERSION},
            ],
        )

    checkpoints = _extract_checkpoints(payload)
    checkpoint_results: list[PipelineTzResult] = []
    missing_indices: list[int] = []
    for index in range(1, task.failed_tz_index):
        item = checkpoints.get(str(index))
        if not item:
            missing_indices.append(index)
            continue
        result_path = file_cache.task_workspace(task.id) / str(item["output_path"])
        if not result_path.is_file():
            missing_indices.append(index)
            continue
        checkpoint_results.append(
            load_tz_pipeline_result(
                package_id=str(item["package_id"]),
                tz_id=str(item["tz_id"]),
                collection_name=str(item["collection_name"]),
                output_path=result_path,
            )
        )

    if missing_indices:
        raise ApiError(
            status_code=409,
            code="restart_checkpoints_missing",
            message="Не найдены промежуточные результаты. Запустите обработку с начала",
            details=[{"field": "checkpoint_indices", "value": missing_indices}],
        )
    return task.failed_tz_index, checkpoint_results


def _load_checkpoints(task_id: str) -> dict[str, Any]:
    payload = _load_checkpoints_payload(task_id)
    return _extract_checkpoints(payload)


def _load_checkpoints_payload(task_id: str) -> dict[str, Any]:
    path = file_cache.checkpoints_path(task_id)
    if not path.is_file():
        return {"checkpoints": {}}
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except ValueError as exc:
        raise ApiError(
            status_code=409,
            code="restart_checkpoints_corrupted",
            message="Промежуточные результаты повреждены. Запустите обработку с начала",
        ) from exc
    if not isinstance(payload, dict):
        return {"checkpoints": {}}
    return payload


def _extract_checkpoints(payload: dict[str, Any]) -> dict[str, Any]:
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, dict):
        return {}
    return checkpoints


def _save_checkpoint(task_id: str, index: int, result: PipelineTzResult) -> None:
    path = file_cache.checkpoints_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"checkpoints": {}, "pipeline_version": PIPELINE_VERSION}
    if path.is_file():
        try:
            with path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
        except ValueError:
            payload = {"checkpoints": {}, "pipeline_version": PIPELINE_VERSION}
    if not isinstance(payload, dict):
        payload = {"checkpoints": {}, "pipeline_version": PIPELINE_VERSION}
    payload["pipeline_version"] = PIPELINE_VERSION
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, dict):
        checkpoints = {}
        payload["checkpoints"] = checkpoints
    checkpoints[str(index)] = {
        "package_id": result.package_id,
        "tz_id": result.tz_id,
        "collection_name": result.collection_name,
        "output_path": str(result.output_path.relative_to(file_cache.task_workspace(task_id))),
        "source_chunks_path": (
            str(result.source_chunks_path.relative_to(file_cache.task_workspace(task_id)))
            if result.source_chunks_path is not None
            else None
        ),
        "pipeline_version": PIPELINE_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _clear_checkpoint_outputs(task_id: str) -> None:
    shutil.rmtree(file_cache.output_dir(task_id), ignore_errors=True)
    shutil.rmtree(file_cache.artifacts_dir(task_id), ignore_errors=True)
    file_cache.ensure_workspace(task_id)


def _pipeline_version_from_checkpoints(task_id: str) -> str:
    payload = _load_checkpoints_payload(task_id)
    return _pipeline_version_from_payload(payload)


def _pipeline_version_from_payload(payload: dict[str, Any]) -> str:
    value = payload.get("pipeline_version")
    if isinstance(value, str) and value.strip():
        return value.strip()

    checkpoints = _extract_checkpoints(payload)
    for item in checkpoints.values():
        if isinstance(item, dict):
            checkpoint_version = item.get("pipeline_version")
            if isinstance(checkpoint_version, str) and checkpoint_version.strip():
                return checkpoint_version.strip()

    # Legacy checkpoints (without pipeline_version): use current version as fallback.
    return PIPELINE_VERSION


def _load_pipeline_config() -> dict[str, Any]:
    """Root config.yaml via infra; optional app-only overrides from config.app.yaml."""
    import yaml

    from infra.config import get_config_and_env

    from backend.app.settings import APP_ROOT

    config = get_config_and_env()
    app_cfg_path = APP_ROOT / "config.app.yaml"
    if app_cfg_path.is_file():
        with app_cfg_path.open(encoding="utf-8") as handle:
            app_cfg = yaml.safe_load(handle) or {}
        if not isinstance(app_cfg, dict):
            raise RuntimeError(f"Invalid app config (expected mapping): {app_cfg_path}")
        # Top-level keys only — do not replace nested MODELS/EMBEDDINGS from root.
        for key, value in app_cfg.items():
            config[key] = value
    return config


def _set_progress(
    task_id: str,
    log_path: Path,
    step: str,
    message: str,
    *,
    progress_tz_id: str,
    progress_tz_index: int,
    progress_tz_total: int,
    progress_execution_variant: str | None = None,
) -> None:
    task_service.set_processing_progress(
        task_id,
        step,
        message,
        progress_tz_id=progress_tz_id,
        progress_tz_index=progress_tz_index,
        progress_tz_total=progress_tz_total,
        progress_execution_variant=progress_execution_variant,
    )
    _append_log(log_path, f"{step}: {message}")


def _append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as file:
        file.write(f"{timestamp} {message}\n")


def _write_error(task_id: str, exc: Exception) -> None:
    path = file_cache.processing_error_path(task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "message": str(exc),
        "type": type(exc).__name__,
        "traceback": traceback.format_exc(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
