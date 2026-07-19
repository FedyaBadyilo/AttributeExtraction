"""Pydantic API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal["draft", "ready", "processing", "done", "error"]
ProcessRestartMode = Literal["from_start", "from_failed_tz"]


class ObjectTypeRead(BaseModel):
    code: str
    title: str
    dataset_dirname: str


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    object_type: str = Field(min_length=1, max_length=128)


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    object_type: str | None = Field(default=None, min_length=1, max_length=128)


class ProcessTaskRequest(BaseModel):
    mode: ProcessRestartMode = "from_start"


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    object_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    registry_file_name: str | None = None
    documents_archive_name: str | None = None
    ground_truth_file_name: str | None = None
    has_ground_truth: bool = False
    result_file_name: str | None = None
    last_validation: str | None = None
    progress_step: str | None = None
    progress_message: str | None = None
    progress_tz_id: str | None = None
    progress_tz_index: int | None = None
    progress_tz_total: int | None = None
    progress_execution_variant: str | None = None
    failed_tz_id: str | None = None
    failed_tz_index: int | None = None
    failed_execution_variant: str | None = None
    error_message: str | None = None


class DocumentFileRead(BaseModel):
    file_name: str
    size_bytes: int
    uploaded_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int
    limit: int
    offset: int


class TzPackageRead(BaseModel):
    package_id: str | None = None
    tz_id: str
    main_file_name: str
    supplements_by_index: dict[int, str]
    recpart: str | None = None
    recpart_source: Literal["file", "synthetic"] = "file"
    execution_variant: str | None = None


class ValidationIssue(BaseModel):
    code: str
    message: str
    field: str | None = None
    tz_id: str | None = None
    file_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    is_valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    packages: list[TzPackageRead] = Field(default_factory=list)
