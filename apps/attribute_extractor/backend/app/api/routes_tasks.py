"""Task and object type endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query, Response

from backend.app.schemas import ObjectTypeRead, TaskCreate, TaskListResponse, TaskRead, TaskStatus, TaskUpdate
from backend.app.services import task_service

router = APIRouter()


@router.get("/object-types", response_model=list[ObjectTypeRead], tags=["object-types"])
def list_object_types() -> list[ObjectTypeRead]:
    return task_service.list_object_types()


@router.get("/tasks", response_model=TaskListResponse, tags=["tasks"])
def list_tasks(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: TaskStatus | None = None,
    search: str | None = None,
    object_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> TaskListResponse:
    return task_service.list_tasks(
        limit=limit,
        offset=offset,
        status=status,
        search=search,
        object_type=object_type,
        created_from=created_from,
        created_to=created_to,
    )


@router.post("/tasks", response_model=TaskRead, status_code=201, tags=["tasks"])
def create_task(payload: TaskCreate) -> TaskRead:
    return task_service.create_task(payload)


@router.get("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
def get_task(task_id: str) -> TaskRead:
    return task_service.get_task_by_id(task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead, tags=["tasks"])
def update_task(task_id: str, payload: TaskUpdate) -> TaskRead:
    return task_service.update_task(task_id, payload)


@router.delete("/tasks/{task_id}", status_code=204, tags=["tasks"])
def delete_task(task_id: str) -> Response:
    task_service.delete_task(task_id)
    return Response(status_code=204)
