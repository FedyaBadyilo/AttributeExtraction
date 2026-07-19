"""Local task workspace file cache."""

from __future__ import annotations

import shutil
import time
from collections.abc import Collection
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.app.errors import ApiError
from backend.app.settings import get_settings


REGISTRY_FILE_STEM = "registry"
REGISTRY_FILE_NAME = "registry.xlsx"
GROUND_TRUTH_FILE_STEM = "ground_truth"
GROUND_TRUTH_FILE_NAME = "ground_truth.xlsx"
GROUND_TRUTH_CANDIDATE_STEM = "ground_truth_candidate"
GROUND_TRUTH_VERSIONED_STEM = "ground_truth_v"
RESULT_FILE_NAME = "result.xlsx"
RESULT_MANIFEST_FILE_NAME = "result_manifest.json"
CHECKPOINTS_FILE_NAME = "tz_checkpoints.json"
EXCEL_EXTENSIONS = (".xlsx", ".xls")


def task_workspace(task_id: str) -> Path:
    return get_settings().cache_dir / "tasks" / task_id


def task_input_dir(task_id: str) -> Path:
    return task_workspace(task_id) / "input"


def documents_dir(task_id: str) -> Path:
    return task_input_dir(task_id) / "documents"


def output_dir(task_id: str) -> Path:
    return task_workspace(task_id) / "output"


def logs_dir(task_id: str) -> Path:
    return task_workspace(task_id) / "logs"


def errors_dir(task_id: str) -> Path:
    return task_workspace(task_id) / "errors"


def processing_log_path(task_id: str) -> Path:
    return logs_dir(task_id) / "processing.log"


def processing_error_path(task_id: str) -> Path:
    return errors_dir(task_id) / "error.json"


def result_path(task_id: str) -> Path:
    return output_dir(task_id) / RESULT_FILE_NAME


def result_manifest_path(task_id: str) -> Path:
    return output_dir(task_id) / RESULT_MANIFEST_FILE_NAME


def checkpoints_path(task_id: str) -> Path:
    return output_dir(task_id) / CHECKPOINTS_FILE_NAME


def artifacts_dir(task_id: str) -> Path:
    return task_workspace(task_id) / "artifacts"


def registry_path(task_id: str) -> Path:
    return _existing_stemmed_file(task_input_dir(task_id), REGISTRY_FILE_STEM) or (
        task_input_dir(task_id) / REGISTRY_FILE_NAME
    )


def ground_truth_path(task_id: str) -> Path:
    return _existing_stemmed_file(task_input_dir(task_id), GROUND_TRUTH_FILE_STEM, include_versioned=True) or (
        task_input_dir(task_id) / GROUND_TRUTH_FILE_NAME
    )


def ensure_workspace(task_id: str) -> Path:
    root = task_workspace(task_id)
    for path in (task_input_dir(task_id), output_dir(task_id), logs_dir(task_id), errors_dir(task_id)):
        path.mkdir(parents=True, exist_ok=True)
    return root


def delete_workspace(task_id: str) -> None:
    shutil.rmtree(task_workspace(task_id), ignore_errors=True)


def clear_runtime_outputs(task_id: str) -> None:
    shutil.rmtree(output_dir(task_id), ignore_errors=True)
    shutil.rmtree(artifacts_dir(task_id), ignore_errors=True)
    shutil.rmtree(logs_dir(task_id), ignore_errors=True)
    shutil.rmtree(errors_dir(task_id), ignore_errors=True)


def _require_extension(filename: str | None, allowed: Collection[str], field: str) -> str:
    name = Path(filename or "").name
    suffix = Path(name).suffix.casefold()
    if not name or suffix not in allowed:
        raise ApiError(
            status_code=400,
            code="unsupported_file_type",
            message="Unsupported file type",
            details=[{"field": field, "value": filename, "allowed": sorted(allowed)}],
        )
    return name


def _stored_excel_name(stem: str, original_name: str) -> str:
    return f"{stem}{Path(original_name).suffix.casefold()}"


def _delete_stemmed_files(directory: Path, stem: str, *, include_versioned: bool = False) -> None:
    for extension in EXCEL_EXTENSIONS:
        (directory / f"{stem}{extension}").unlink(missing_ok=True)
    if include_versioned:
        for extension in EXCEL_EXTENSIONS:
            for path in directory.glob(f"{stem}_*{extension}"):
                path.unlink(missing_ok=True)


def _existing_stemmed_file(directory: Path, stem: str, *, include_versioned: bool = False) -> Path | None:
    candidates: list[Path] = []
    for extension in EXCEL_EXTENSIONS:
        path = directory / f"{stem}{extension}"
        if path.is_file():
            candidates.append(path)
    if include_versioned:
        for extension in EXCEL_EXTENSIONS:
            for path in directory.glob(f"{stem}_*{extension}"):
                if path.is_file():
                    candidates.append(path)
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate.stat().st_mtime)


def _write_upload(file: UploadFile, destination: Path) -> int:
    destination.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with destination.open("wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            out.write(chunk)
    return size


def _safe_document_name(filename: str | None) -> str:
    name = Path(filename or "").name
    if not name or name in {".", ".."}:
        raise ApiError(
            status_code=400,
            code="invalid_file_name",
            message="Invalid file name",
            details=[{"field": "documents", "value": filename}],
        )
    return name


def save_registry(task_id: str, file: UploadFile) -> tuple[str, int]:
    original_name = _require_extension(file.filename, EXCEL_EXTENSIONS, "registry")
    ensure_workspace(task_id)
    _delete_stemmed_files(task_input_dir(task_id), REGISTRY_FILE_STEM)
    size = _write_upload(
        file,
        task_input_dir(task_id) / _stored_excel_name(REGISTRY_FILE_STEM, original_name),
    )
    return original_name, size


def list_documents(task_id: str) -> list[Path]:
    directory = documents_dir(task_id)
    if not directory.is_dir():
        return []
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix == ".pdf"),
        key=lambda path: path.name,
    )


def save_document(task_id: str, file: UploadFile, *, overwrite: bool) -> tuple[str, int]:
    original_name = _safe_document_name(file.filename)
    if Path(original_name).suffix != ".pdf":
        raise ApiError(
            status_code=400,
            code="unsupported_file_type",
            message="Unsupported file type",
            details=[{"field": "documents", "value": file.filename, "allowed": [".pdf"]}],
        )
    ensure_workspace(task_id)
    destination = documents_dir(task_id) / original_name
    if destination.exists() and not overwrite:
        raise ApiError(
            status_code=409,
            code="document_already_exists",
            message="Document with the same name already exists",
            details=[{"field": "documents", "file_name": original_name}],
        )
    size = _write_upload(file, destination)
    return original_name, size


def document_path(task_id: str, file_name: str) -> Path:
    return documents_dir(task_id) / _safe_document_name(file_name)


def delete_document(task_id: str, file_name: str) -> None:
    target = document_path(task_id, file_name)
    if not target.is_file():
        raise ApiError(
            status_code=404,
            code="document_not_found",
            message="Document file not found",
            details=[{"field": "documents", "file_name": target.name}],
        )
    target.unlink()


def save_ground_truth(task_id: str, file: UploadFile) -> tuple[str, int]:
    original_name = _require_extension(file.filename, EXCEL_EXTENSIONS, "ground_truth")
    ensure_workspace(task_id)
    _delete_stemmed_files(task_input_dir(task_id), GROUND_TRUTH_FILE_STEM)
    size = _write_upload(
        file,
        task_input_dir(task_id) / _stored_excel_name(GROUND_TRUTH_FILE_STEM, original_name),
    )
    return original_name, size


def save_ground_truth_candidate(task_id: str, file: UploadFile) -> tuple[str, Path, int]:
    original_name = _require_extension(file.filename, EXCEL_EXTENSIONS, "ground_truth")
    ensure_workspace(task_id)
    ext = Path(original_name).suffix.casefold()
    destination = task_input_dir(task_id) / f"{GROUND_TRUTH_CANDIDATE_STEM}_{uuid4().hex}{ext}"
    size = _write_upload(file, destination)
    return original_name, destination, size


def commit_ground_truth_candidate(task_id: str, candidate_path: Path, original_name: str) -> None:
    if not candidate_path.is_file():
        raise ApiError(
            status_code=409,
            code="ground_truth_candidate_missing",
            message="Временный файл эталонных данных недоступен; повторите загрузку",
        )
    input_dir = task_input_dir(task_id)
    ext = Path(original_name).suffix.casefold()
    destination = input_dir / f"{GROUND_TRUTH_VERSIONED_STEM}_{uuid4().hex}{ext}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    existing_versioned: list[Path] = []
    for extension in EXCEL_EXTENSIONS:
        existing_versioned.extend(input_dir.glob(f"{GROUND_TRUTH_VERSIONED_STEM}_*{extension}"))
    try:
        _delete_stemmed_files(input_dir, GROUND_TRUTH_FILE_STEM)
        shutil.copyfile(candidate_path, destination)
        for stale in existing_versioned:
            if stale != destination:
                stale.unlink(missing_ok=True)
    except Exception as exc:  # pragma: no cover - defensive guard around filesystem race conditions
        destination.unlink(missing_ok=True)
        raise ApiError(
            status_code=500,
            code="ground_truth_store_failed",
            message="Не удалось сохранить файл эталонных данных",
            details=[
                {
                    "field": "ground_truth",
                    "code": "ground_truth_store_failed",
                    "message": "Ошибка сохранения файла эталонных данных",
                    "details": {"error": str(exc)},
                }
            ],
        ) from exc
    finally:
        candidate_path.unlink(missing_ok=True)

    if not _wait_until_file_visible(destination):
        resolved = _existing_stemmed_file(input_dir, GROUND_TRUTH_VERSIONED_STEM, include_versioned=True)
        if resolved and resolved.is_file():
            return
        raise ApiError(
            status_code=500,
            code="ground_truth_store_failed",
            message="Не удалось сохранить файл эталонных данных",
            details=[
                {
                    "field": "ground_truth",
                    "code": "ground_truth_store_failed",
                    "message": "Файл эталонных данных не найден после сохранения",
                    "details": {"error": "committed_file_missing"},
                }
            ],
        )


def _wait_until_file_visible(path: Path, *, retries: int = 8, delay_seconds: float = 0.05) -> bool:
    for _ in range(retries):
        if path.is_file():
            return True
        time.sleep(delay_seconds)
    return path.is_file()


def delete_ground_truth_candidate(task_id: str, candidate_path: Path | None = None) -> None:
    if candidate_path is not None:
        candidate_path.unlink(missing_ok=True)
        return
    for path in task_input_dir(task_id).glob(f"{GROUND_TRUTH_CANDIDATE_STEM}_*"):
        path.unlink(missing_ok=True)


def delete_ground_truth(task_id: str) -> None:
    input_dir = task_input_dir(task_id)
    _delete_stemmed_files(input_dir, GROUND_TRUTH_FILE_STEM)
    _delete_stemmed_files(input_dir, GROUND_TRUTH_VERSIONED_STEM, include_versioned=True)


def delete_result(task_id: str) -> None:
    result_path(task_id).unlink(missing_ok=True)
    result_manifest_path(task_id).unlink(missing_ok=True)


def delete_documents(task_id: str) -> None:
    shutil.rmtree(documents_dir(task_id), ignore_errors=True)
