"""Validation endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas import ValidationReport
from backend.app.services import registry_validation, task_service

router = APIRouter(tags=["validation"])


@router.post("/tasks/{task_id}/validate", response_model=ValidationReport)
def validate_task_sources(task_id: str) -> ValidationReport:
    task_service.ensure_source_files_editable(task_id)
    report = registry_validation.validate_task_sources(task_id)
    task_service.set_validation_report(task_id, report)
    return report
