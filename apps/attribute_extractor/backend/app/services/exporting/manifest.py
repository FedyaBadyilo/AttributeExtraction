from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.schemas import TaskRead
from backend.app.services import file_cache
from backend.app.services.exporting.config import EXPORT_FORMAT_VERSION


def result_manifest_matches(task: TaskRead, *, pipeline_version: str) -> bool:
    path = file_cache.result_manifest_path(task.id)
    if not path.is_file():
        return False
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return False
    current_ground_truth_fingerprint = ground_truth_fingerprint(task)
    if task.has_ground_truth and current_ground_truth_fingerprint is None:
        return False
    return (
        manifest.get("format_version") == EXPORT_FORMAT_VERSION
        and manifest.get("pipeline_version") == pipeline_version
        and manifest.get("has_ground_truth") is task.has_ground_truth
        and manifest.get("ground_truth_file_name") == task.ground_truth_file_name
        and manifest.get("ground_truth_fingerprint") == current_ground_truth_fingerprint
    )


def write_result_manifest(task: TaskRead, *, pipeline_version: str) -> None:
    path = file_cache.result_manifest_path(task.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": EXPORT_FORMAT_VERSION,
        "pipeline_version": pipeline_version,
        "has_ground_truth": task.has_ground_truth,
        "ground_truth_file_name": task.ground_truth_file_name,
        "ground_truth_fingerprint": ground_truth_fingerprint(task),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ground_truth_fingerprint(task: TaskRead) -> str | None:
    if not task.has_ground_truth:
        return None
    path = file_cache.ground_truth_path(task.id)
    if not path.is_file():
        return None
    return file_fingerprint(path)


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"
