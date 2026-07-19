"""SQLite connection and schema initialization."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.app.constants import DEFAULT_OBJECT_TYPES
from backend.app.settings import Settings, get_settings


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS object_types (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    dataset_dirname TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    object_type TEXT NOT NULL REFERENCES object_types(code),
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    registry_file_name TEXT,
    documents_archive_name TEXT,
    ground_truth_file_name TEXT,
    has_ground_truth INTEGER NOT NULL DEFAULT 0,
    result_file_name TEXT,
    last_validation TEXT,
    progress_step TEXT,
    progress_message TEXT,
    progress_tz_id TEXT,
    progress_tz_index INTEGER,
    progress_tz_total INTEGER,
    progress_execution_variant TEXT,
    failed_tz_id TEXT,
    failed_tz_index INTEGER,
    failed_execution_variant TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS task_documents_archive (
    task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
    original_name TEXT NOT NULL,
    stored_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    extracted_pdf_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reference_data (
    object_type TEXT NOT NULL REFERENCES object_types(code),
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (object_type, kind)
);
"""


def connect(settings: Settings | None = None) -> sqlite3.Connection:
    settings = settings or get_settings()
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.sqlite_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def db_connection(settings: Settings | None = None) -> Iterator[sqlite3.Connection]:
    connection = connect(settings)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    with db_connection(settings) as connection:
        connection.executescript(SCHEMA_SQL)
        _migrate_tasks_table(connection)
        connection.executemany(
            """
            INSERT INTO object_types (code, title, dataset_dirname)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                title = excluded.title,
                dataset_dirname = excluded.dataset_dirname
            """,
            DEFAULT_OBJECT_TYPES,
        )
        _mark_interrupted_processing_tasks(connection)

    from backend.app.services.reference_data import seed_reference_data

    seed_reference_data(settings)


def _mark_interrupted_processing_tasks(connection: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    connection.execute(
        """
        UPDATE tasks
        SET
            status = 'error',
            updated_at = ?,
            progress_step = NULL,
            progress_message = NULL,
            failed_tz_id = progress_tz_id,
            failed_tz_index = progress_tz_index,
            failed_execution_variant = progress_execution_variant,
            error_message = 'Обработка прервалась из-за перезапуска сервиса'
        WHERE status = 'processing'
        """,
        (now,),
    )


def _migrate_tasks_table(connection: sqlite3.Connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(tasks)").fetchall()
    }
    columns: dict[str, str] = {
        "progress_tz_id": "TEXT",
        "progress_tz_index": "INTEGER",
        "progress_tz_total": "INTEGER",
        "progress_execution_variant": "TEXT",
        "failed_tz_id": "TEXT",
        "failed_tz_index": "INTEGER",
        "failed_execution_variant": "TEXT",
    }
    for name, definition in columns.items():
        if name not in existing_columns:
            connection.execute(f"ALTER TABLE tasks ADD COLUMN {name} {definition}")
