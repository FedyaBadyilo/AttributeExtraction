"""Task file upload endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse

from backend.app.constants import REGISTRY_TEMPLATE_FILENAME
from backend.app.errors import ApiError
from backend.app.schemas import DocumentFileRead, TaskRead, ValidationReport
from backend.app.services import file_cache, ground_truth_validation, reference_data, task_service
from backend.app.settings import get_settings

router = APIRouter(tags=["task-files"])


@router.get("/registry-template", tags=["registry-templates"])
def download_registry_template() -> FileResponse:
    template_path = get_settings().registry_templates_dir / REGISTRY_TEMPLATE_FILENAME
    if not template_path.is_file():
        raise _registry_template_not_found()

    return FileResponse(
        template_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="registry-template.xlsx",
    )


@router.post("/tasks/{task_id}/registry", response_model=TaskRead)
def upload_registry(task_id: str, file: UploadFile = File(...)) -> TaskRead:
    task_service.ensure_source_files_editable(task_id)
    original_name, _ = file_cache.save_registry(task_id, file)
    return task_service.set_registry_file(task_id, original_name)


@router.get("/tasks/{task_id}/registry")
def download_registry(task_id: str) -> FileResponse:
    task = task_service.get_task_by_id(task_id)
    path = file_cache.registry_path(task_id)
    if not path.is_file():
        raise _registry_not_found()
    return _file_download(path, task.registry_file_name or path.name)


@router.get("/tasks/{task_id}/documents", response_model=list[DocumentFileRead])
def list_documents(task_id: str) -> list[DocumentFileRead]:
    task_service.get_task_by_id(task_id)
    items: list[DocumentFileRead] = []
    for path in file_cache.list_documents(task_id):
        stat = path.stat()
        items.append(
            DocumentFileRead(
                file_name=path.name,
                size_bytes=int(stat.st_size),
                uploaded_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            )
        )
    return items


@router.post("/tasks/{task_id}/documents", response_model=TaskRead)
def upload_documents(task_id: str, overwrite: bool = Form(False), file: UploadFile = File(...)) -> TaskRead:
    task_service.ensure_source_files_editable(task_id)
    file_cache.save_document(task_id, file, overwrite=overwrite)
    return task_service.mark_source_files_changed(task_id)


@router.get("/tasks/{task_id}/documents/{file_name:path}")
def download_document(task_id: str, file_name: str) -> FileResponse:
    task_service.get_task_by_id(task_id)
    path = file_cache.document_path(task_id, file_name)
    if not path.is_file():
        raise ApiError(
            status_code=404,
            code="document_not_found",
            message="Document file not found",
            details=[{"field": "documents", "file_name": path.name}],
        )
    return _file_download(path, path.name, media_type="application/pdf")


@router.delete("/tasks/{task_id}/documents/{file_name:path}", response_model=TaskRead)
def delete_documents(task_id: str, file_name: str) -> TaskRead:
    task_service.ensure_source_files_editable(task_id)
    file_cache.delete_document(task_id, Path(file_name).name)
    return task_service.mark_source_files_changed(task_id)


@router.post("/tasks/{task_id}/ground-truth", response_model=TaskRead)
def upload_ground_truth(task_id: str, file: UploadFile = File(...)) -> TaskRead:
    task = task_service.ensure_ground_truth_editable(task_id)
    report = _require_valid_last_validation(task)
    expected_recparts = ground_truth_validation.expected_recparts_from_report(report)
    attributes_set = reference_data.load_attributes_set(task.object_type)
    original_name, candidate_path, _ = file_cache.save_ground_truth_candidate(task_id, file)
    issues = ground_truth_validation.validate_ground_truth_file(candidate_path, expected_recparts, attributes_set)
    if issues:
        file_cache.delete_ground_truth_candidate(task_id, candidate_path)
        raise ApiError(
            status_code=400,
            code="ground_truth_recpart_mismatch",
            message="Эталонные данные не соответствуют текущему реестру",
            details=[issue.model_dump() for issue in issues],
        )
    file_cache.commit_ground_truth_candidate(task_id, candidate_path, original_name)
    return task_service.set_ground_truth_file(task_id, original_name)


@router.post("/tasks/{task_id}/ground-truth/validate", response_model=ValidationReport)
def validate_ground_truth(task_id: str) -> ValidationReport:
    task = task_service.get_task_by_id(task_id)
    report = _require_valid_last_validation(task)
    if not task.has_ground_truth:
        raise ApiError(
            status_code=409,
            code="ground_truth_missing",
            message="Файл эталонных данных не загружен",
        )

    ground_truth_path = file_cache.ground_truth_path(task_id)
    expected_recparts = ground_truth_validation.expected_recparts_from_report(report)
    attributes_set = reference_data.load_attributes_set(task.object_type)
    issues = ground_truth_validation.validate_ground_truth_file(ground_truth_path, expected_recparts, attributes_set)
    return ValidationReport(
        is_valid=not issues,
        issues=issues,
        packages=report.packages,
    )


@router.get("/tasks/{task_id}/ground-truth")
def download_ground_truth(task_id: str) -> FileResponse:
    task = task_service.get_task_by_id(task_id)
    if not task.has_ground_truth:
        raise _ground_truth_not_found()
    path = file_cache.ground_truth_path(task_id)
    if not path.is_file():
        raise _ground_truth_not_found()
    return _file_download(path, task.ground_truth_file_name or path.name)


@router.delete("/tasks/{task_id}/ground-truth", response_model=TaskRead)
def delete_ground_truth(task_id: str) -> TaskRead:
    task_service.ensure_ground_truth_editable(task_id)
    file_cache.delete_ground_truth(task_id)
    return task_service.clear_ground_truth_file(task_id)


def _file_download(path: Path, filename: str, *, media_type: str | None = None) -> FileResponse:
    resolved_media_type = media_type or _media_type_for_path(path)
    return FileResponse(
        path,
        media_type=resolved_media_type,
        filename=filename,
        headers={"Cache-Control": "no-store"},
    )


def _media_type_for_path(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix == ".xls":
        return "application/vnd.ms-excel"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _registry_not_found() -> ApiError:
    return ApiError(
        status_code=404,
        code="registry_not_found",
        message="Файл реестра не загружен",
    )


def _ground_truth_not_found() -> ApiError:
    return ApiError(
        status_code=404,
        code="ground_truth_not_found",
        message="Файл эталонных данных не загружен",
    )


def _require_valid_last_validation(task: TaskRead) -> ValidationReport:
    if not task.last_validation:
        raise ApiError(
            status_code=409,
            code="task_validation_missing",
            message="Сначала выполните успешную проверку исходного комплекта",
        )
    try:
        report = ValidationReport.model_validate_json(task.last_validation)
    except ValueError as exc:
        raise ApiError(
            status_code=409,
            code="task_validation_invalid",
            message="Отчет проверки исходного комплекта не читается",
            details=[{"field": "last_validation", "error": str(exc)}],
        ) from exc
    if not report.is_valid:
        raise ApiError(
            status_code=409,
            code="task_validation_not_successful",
            message="Сначала исправьте ошибки исходного комплекта",
        )
    return report


def _registry_template_not_found() -> ApiError:
    return ApiError(
        status_code=404,
        code="registry_template_not_found",
        message="Шаблон реестра еще не подготовлен",
    )
