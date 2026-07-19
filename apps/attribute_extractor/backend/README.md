# Attribute Extractor Backend

Pilot FastAPI backend for task management and pipeline orchestration.

## Run locally

From repository root:

```bash
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

Health check:

```text
GET /health
```

## Processing

Start or restart processing:

```text
POST /tasks/{task_id}/process
Content-Type: application/json

{"mode": "from_start"}
```

`mode` is optional and defaults to `from_start` for backward compatibility.

Supported modes:

- `from_start` - process the task from the first TZ and replace previous runtime output.
- `from_failed_tz` - available only after a task fails inside a concrete TZ. The backend reuses saved successful TZ checkpoints and resumes from `failed_tz_id`. If registry/documents were changed, checkpoints are removed and this mode is rejected.

Ground Truth changes do not block `from_failed_tz`, because GT is not part of the extraction pipeline run.

## Runtime data

By default the backend stores local runtime data in:

```text
backend/.cache/
```

The SQLite database is created automatically at startup:

```text
backend/.cache/backend.sqlite3
```

The SQLite file is a runtime artifact and should not be committed.

## Reference Data

Git-tracked seed JSON files live in:

```text
backend/reference_data/
```

On startup, the backend validates these files and imports them into SQLite.
The SQLite copy is runtime state; the JSON files are the source of truth for now.
