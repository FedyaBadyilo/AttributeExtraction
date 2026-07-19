# Attribute Extractor (MVP app)

FastAPI + React UI for: create task → upload registry/PDFs → validate → process → export.

Layout follows the monorepo rules:

- App code: `apps/attribute_extractor/{backend,frontend}`
- Pipeline: `research/steps/*/domain` (orchestrated by `backend/app/pipeline/runner.py`)
- Shared config: repository root `config.yaml` via `infra.config`
- App-only overrides: `config.app.yaml` (e.g. Qdrant collection template)
- Reference seed (attribute sets / grouping / units): `backend/reference_data/` → SQLite on startup
- Runtime inputs: user uploads (not baked into the image)

## Docker Compose

From this directory:

```bash
docker compose up --build
```

- UI: http://localhost:5173
- API / Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

Default image installs **API deps only** (create task, upload, validate, export of finished runs).
For live `/process` (OCR → … → extraction) rebuild with pipeline deps:

```bash
INSTALL_PIPELINE=1 docker compose up --build
```

Secrets: monorepo root `.env` (see root `.env.example`) and/or local `.env` next to this compose file.

## Local (without Docker)

From the **repository root**:

```bash
export PYTHONPATH="$(pwd):$(pwd)/apps/attribute_extractor"
pip install -r requirements.txt -r requirements.research.txt
pip install -r apps/attribute_extractor/backend/requirements.txt
cd apps/attribute_extractor
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend (Node 20+):

```bash
cd apps/attribute_extractor/frontend && npm ci && npm run dev
```

## Smoke test (API + UI proxy)

With compose up:

```bash
# needs openpyxl in a local venv
python scripts/smoke_api_ui.py
# or: pytest -m integration
```

Covers task CRUD, registry/PDF upload, validate, process start, mocked result download, and the same flow via `http://localhost:5173/api`.

## Unit tests (optional, local)

```bash
pip install -r backend/requirements-dev.txt pydantic pandas openpyxl
PYTHONPATH="$(pwd):$(pwd)/../.." pytest -m "not integration"
```

GitLab CI (root [`.gitlab-ci.yml`](../../.gitlab-ci.yml)) only rebuilds Compose images — same as local `docker compose build`.
