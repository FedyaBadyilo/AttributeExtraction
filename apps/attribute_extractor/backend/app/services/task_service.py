"""Task and object type persistence service."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.app.db import db_connection
from backend.app.errors import ApiError, not_found
from backend.app.schemas import ObjectTypeRead, TaskCreate, TaskListResponse, TaskRead, TaskUpdate, ValidationReport
from backend.app.services import file_cache


EDITABLE_TASK_STATUSES = {"draft", "ready", "error"}
METADATA_EDITABLE_TASK_STATUSES = EDITABLE_TASK_STATUSES | {"done"}
GROUND_TRUTH_EDITABLE_STATUSES = {"draft", "ready", "error", "done"}
PROCESSABLE_TASK_STATUSES = {"ready", "done", "error"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_task(row: sqlite3.Row) -> TaskRead:
    data = dict(row)
    data["has_ground_truth"] = bool(data["has_ground_truth"])
    return TaskRead.model_validate(data)


def _reset_status_after_source_change(task: TaskRead) -> dict[str, Any]:
    file_cache.clear_runtime_outputs(task.id)
    changes: dict[str, Any] = {
        "updated_at": _now_iso(),
        "last_validation": None,
        "progress_step": None,
        "progress_message": None,
        "progress_tz_id": None,
        "progress_tz_index": None,
        "progress_tz_total": None,
        "progress_execution_variant": None,
        "failed_tz_id": None,
        "failed_tz_index": None,
        "failed_execution_variant": None,
        "error_message": None,
        "result_file_name": None,
    }
    if task.status in {"ready", "error", "done"}:
        changes["status"] = "draft"
    return changes


def _invalidate_ground_truth_after_source_change(task: TaskRead, changes: dict[str, Any]) -> None:
    if not task.has_ground_truth and not task.ground_truth_file_name:
        return
    file_cache.delete_ground_truth(task.id)
    changes["has_ground_truth"] = 0
    changes["ground_truth_file_name"] = None


def _apply_task_update(connection: sqlite3.Connection, task_id: str, changes: dict[str, Any]) -> None:
    set_sql = ", ".join(f"{key} = ?" for key in changes)
    connection.execute(
        f"UPDATE tasks SET {set_sql} WHERE id = ?",
        [*changes.values(), task_id],
    )


def _ensure_source_editable(task: TaskRead) -> None:
    if task.status not in EDITABLE_TASK_STATUSES:
        raise ApiError(
            status_code=409,
            code="task_source_not_editable",
            message="Task source files cannot be changed in current status",
            details=[{"field": "status", "value": task.status}],
        )


def _ensure_ground_truth_editable(task: TaskRead) -> None:
    if task.status not in GROUND_TRUTH_EDITABLE_STATUSES:
        raise ApiError(
            status_code=409,
            code="ground_truth_not_editable",
            message="Ground Truth cannot be changed in current status",
            details=[{"field": "status", "value": task.status}],
        )


def ensure_source_files_editable(task_id: str) -> TaskRead:
    task = get_task_by_id(task_id)
    _ensure_source_editable(task)
    return task


def ensure_ground_truth_editable(task_id: str) -> TaskRead:
    task = get_task_by_id(task_id)
    _ensure_ground_truth_editable(task)
    return task


def list_object_types() -> list[ObjectTypeRead]:
    with db_connection() as connection:
        rows = connection.execute(
            """
            SELECT code, title, dataset_dirname
            FROM object_types
            ORDER BY title
            """
        ).fetchall()
    return [ObjectTypeRead.model_validate(dict(row)) for row in rows]


def get_object_type_title(code: str) -> str:
    with db_connection() as connection:
        row = connection.execute(
            "SELECT title FROM object_types WHERE code = ?",
            (code,),
        ).fetchone()
    return str(row["title"]) if row else code


def object_type_exists(connection: sqlite3.Connection, code: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM object_types WHERE code = ?",
        (code,),
    ).fetchone()
    return row is not None


def create_task(payload: TaskCreate) -> TaskRead:
    now = _now_iso()
    task_id = str(uuid4())
    with db_connection() as connection:
        if not object_type_exists(connection, payload.object_type):
            raise ApiError(
                status_code=400,
                code="unknown_object_type",
                message="Unknown object type",
                details=[{"field": "object_type", "value": payload.object_type}],
            )
        try:
            connection.execute(
                """
                INSERT INTO tasks (
                    id, name, object_type, status, created_at, updated_at, has_ground_truth
                )
                VALUES (?, ?, ?, 'draft', ?, ?, 0)
                """,
                (task_id, payload.name.strip(), payload.object_type, now, now),
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc).upper():
                raise ApiError(
                    status_code=409,
                    code="task_name_conflict",
                    message="Task name already exists",
                    details=[{"field": "name", "value": payload.name}],
                ) from exc
            raise
        return get_task(task_id, connection=connection)


def get_task(task_id: str, *, connection: sqlite3.Connection | None = None) -> TaskRead:
    if connection is None:
        with db_connection() as owned_connection:
            return get_task(task_id, connection=owned_connection)

    row = connection.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ?
        """,
        (task_id,),
    ).fetchone()
    if row is None:
        raise not_found("task", task_id)
    return _row_to_task(row)


def get_task_by_id(task_id: str) -> TaskRead:
    with db_connection() as connection:
        return get_task(task_id, connection=connection)


def list_tasks(
    *,
    limit: int,
    offset: int,
    status: str | None = None,
    search: str | None = None,
    object_type: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> TaskListResponse:
    where: list[str] = []
    params: list[Any] = []

    if status:
        where.append("status = ?")
        params.append(status)
    if search:
        where.append("name LIKE ?")
        params.append(f"%{search}%")
    if object_type:
        where.append("object_type = ?")
        params.append(object_type)
    if created_from:
        where.append("created_at >= ?")
        params.append(created_from.isoformat())
    if created_to:
        where.append("created_at <= ?")
        params.append(created_to.isoformat())

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    with db_connection() as connection:
        total = int(
            connection.execute(
                f"SELECT COUNT(*) AS count FROM tasks {where_sql}",
                params,
            ).fetchone()["count"]
        )
        rows = connection.execute(
            f"""
            SELECT *
            FROM tasks
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    return TaskListResponse(
        items=[_row_to_task(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


def update_task(task_id: str, payload: TaskUpdate) -> TaskRead:
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return get_task_by_id(task_id)

    if "name" in updates and updates["name"] is not None:
        updates["name"] = updates["name"].strip()

    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        if current.status not in METADATA_EDITABLE_TASK_STATUSES:
            raise ApiError(
                status_code=409,
                code="task_not_editable",
                message="Task cannot be edited in current status",
                details=[{"field": "status", "value": current.status}],
            )
        if "object_type" in updates and updates["object_type"] is not None:
            if not object_type_exists(connection, updates["object_type"]):
                raise ApiError(
                    status_code=400,
                    code="unknown_object_type",
                    message="Unknown object type",
                    details=[{"field": "object_type", "value": updates["object_type"]}],
                )

        changed = {
            key: value
            for key, value in updates.items()
            if value is not None and getattr(current, key) != value
        }
        if not changed:
            return current

        if "object_type" in changed:
            changed.update(_reset_status_after_source_change(current))
            _invalidate_ground_truth_after_source_change(current, changed)

        changed["updated_at"] = _now_iso()
        set_sql = ", ".join(f"{key} = ?" for key in changed)
        try:
            connection.execute(
                f"UPDATE tasks SET {set_sql} WHERE id = ?",
                [*changed.values(), task_id],
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE" in str(exc).upper():
                raise ApiError(
                    status_code=409,
                    code="task_name_conflict",
                    message="Task name already exists",
                    details=[{"field": "name", "value": updates.get("name")}],
                ) from exc
            raise
        return get_task(task_id, connection=connection)


def delete_task(task_id: str) -> None:
    with db_connection() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise not_found("task", task_id)
    file_cache.delete_workspace(task_id)


def set_registry_file(task_id: str, original_name: str) -> TaskRead:
    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        _ensure_source_editable(current)
        changes = _reset_status_after_source_change(current)
        _invalidate_ground_truth_after_source_change(current, changes)
        changes["registry_file_name"] = original_name
        _apply_task_update(connection, task_id, changes)
        return get_task(task_id, connection=connection)


def mark_source_files_changed(task_id: str) -> TaskRead:
    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        _ensure_source_editable(current)
        changes = _reset_status_after_source_change(current)
        _invalidate_ground_truth_after_source_change(current, changes)
        changes["documents_archive_name"] = None
        _apply_task_update(connection, task_id, changes)
        return get_task(task_id, connection=connection)


def set_ground_truth_file(task_id: str, original_name: str) -> TaskRead:
    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        _ensure_ground_truth_editable(current)
        file_cache.delete_result(task_id)
        _apply_task_update(
            connection,
            task_id,
            {
                "ground_truth_file_name": original_name,
                "has_ground_truth": 1,
                "result_file_name": None,
                "updated_at": _now_iso(),
            },
        )
        return get_task(task_id, connection=connection)


def clear_ground_truth_file(task_id: str) -> TaskRead:
    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        _ensure_ground_truth_editable(current)
        file_cache.delete_result(task_id)
        _apply_task_update(
            connection,
            task_id,
            {
                "ground_truth_file_name": None,
                "has_ground_truth": 0,
                "result_file_name": None,
                "updated_at": _now_iso(),
            },
        )
        return get_task(task_id, connection=connection)


def set_validation_report(task_id: str, report: ValidationReport) -> TaskRead:
    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        _ensure_source_editable(current)
        _apply_task_update(
            connection,
            task_id,
            {
                "last_validation": report.model_dump_json(),
                "status": "ready" if report.is_valid else "draft",
                "updated_at": _now_iso(),
                "progress_step": None,
                "progress_message": None,
                "progress_tz_id": None,
                "progress_tz_index": None,
                "progress_tz_total": None,
                "progress_execution_variant": None,
                "failed_tz_id": None,
                "failed_tz_index": None,
                "failed_execution_variant": None,
                "error_message": None,
            },
        )
        return get_task(task_id, connection=connection)


def start_processing(task_id: str, *, progress_tz_total: int | None = None) -> TaskRead:
    with db_connection() as connection:
        current = get_task(task_id, connection=connection)
        if current.status == "processing":
            raise ApiError(
                status_code=409,
                code="task_already_processing",
                message="Задача уже обрабатывается",
                details=[{"field": "status", "value": current.status}],
            )
        if current.status not in PROCESSABLE_TASK_STATUSES:
            raise ApiError(
                status_code=409,
                code="task_not_ready_for_processing",
                message="Задача пока не готова к обработке",
                details=[{"field": "status", "value": current.status}],
            )
        if not current.last_validation:
            raise ApiError(
                status_code=409,
                code="task_validation_missing",
                message="Перед обработкой нужно проверить комплект файлов",
            )

        changes = {
            "status": "processing",
            "updated_at": _now_iso(),
            "progress_step": "validate_input",
            "progress_message": "Подготовка задачи к обработке",
            "progress_tz_id": None,
            "progress_tz_index": None,
            "progress_tz_total": progress_tz_total,
            "progress_execution_variant": None,
            "failed_tz_id": None,
            "failed_tz_index": None,
            "failed_execution_variant": None,
            "error_message": None,
            "result_file_name": None,
        }
        _apply_task_update(connection, task_id, changes)
        return get_task(task_id, connection=connection)


def set_processing_progress(
    task_id: str,
    step: str,
    message: str,
    *,
    progress_tz_id: str | None = None,
    progress_tz_index: int | None = None,
    progress_tz_total: int | None = None,
    progress_execution_variant: str | None = None,
    clear_progress_tz_id: bool = False,
    clear_progress_execution_variant: bool = False,
) -> TaskRead:
    with db_connection() as connection:
        get_task(task_id, connection=connection)
        changes: dict[str, Any] = {
            "updated_at": _now_iso(),
            "progress_step": step,
            "progress_message": message,
        }
        if clear_progress_tz_id:
            changes["progress_tz_id"] = None
        elif progress_tz_id is not None:
            changes["progress_tz_id"] = progress_tz_id
        if clear_progress_execution_variant or clear_progress_tz_id:
            changes["progress_execution_variant"] = None
        elif progress_execution_variant is not None:
            changes["progress_execution_variant"] = progress_execution_variant
        if progress_tz_index is not None:
            changes["progress_tz_index"] = progress_tz_index
        if progress_tz_total is not None:
            changes["progress_tz_total"] = progress_tz_total
        _apply_task_update(connection, task_id, changes)
        return get_task(task_id, connection=connection)


def finish_processing_success(task_id: str, result_file_name: str) -> TaskRead:
    with db_connection() as connection:
        get_task(task_id, connection=connection)
        _apply_task_update(
            connection,
            task_id,
            {
                "status": "done",
                "updated_at": _now_iso(),
                "result_file_name": result_file_name,
                "progress_step": "done",
                "progress_message": "Обработка завершена",
                "progress_tz_id": None,
                "progress_execution_variant": None,
                "error_message": None,
            },
        )
        return get_task(task_id, connection=connection)


def finish_processing_error(
    task_id: str,
    message: str,
    *,
    failed_tz_id: str | None = None,
    failed_tz_index: int | None = None,
    failed_execution_variant: str | None = None,
) -> TaskRead:
    with db_connection() as connection:
        get_task(task_id, connection=connection)
        _apply_task_update(
            connection,
            task_id,
            {
                "status": "error",
                "updated_at": _now_iso(),
                "progress_step": None,
                "progress_message": None,
                "progress_execution_variant": None,
                "failed_tz_id": failed_tz_id,
                "failed_tz_index": failed_tz_index,
                "failed_execution_variant": failed_execution_variant,
                "error_message": message,
            },
        )
        return get_task(task_id, connection=connection)
