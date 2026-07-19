"""Task processing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import FileResponse

from backend.app.schemas import ProcessTaskRequest, TaskRead
from backend.app.services import processing_service

router = APIRouter(tags=["processing"])


@router.post("/tasks/{task_id}/process", response_model=TaskRead)
def process_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    payload: ProcessTaskRequest | None = None,
) -> TaskRead:
    request = payload or ProcessTaskRequest()
    plan = processing_service.enqueue_processing(task_id, request.mode)
    background_tasks.add_task(processing_service.process_task, task_id, plan)
    return plan.task


@router.get("/tasks/{task_id}/result")
def download_result(task_id: str) -> FileResponse:
    result = processing_service.result_download(task_id)
    return FileResponse(
        path=result.path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=result.filename,
        headers={"Cache-Control": "no-store"},
    )
