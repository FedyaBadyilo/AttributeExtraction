"""Artifact writing and all-or-nothing publication for benchmark runs."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from research.benchmarks.document_parsing.models import BenchmarkManifest


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_run_metadata(
    staging_dir: Path,
    *,
    manifest: BenchmarkManifest,
    dataset_digest: str,
) -> None:
    (staging_dir / ".gitkeep").touch()
    write_json(
        staging_dir / "manifest.snapshot.json",
        manifest.model_dump(mode="json"),
    )
    (staging_dir / "dataset.digest").write_text(dataset_digest + "\n", encoding="ascii")


def write_case_artifacts(
    staging_dir: Path,
    *,
    case_id: str,
    reference_bytes: bytes,
    prediction: str,
    ocr: Any,
    formatted: Any,
) -> None:
    case_dir = staging_dir / "cases" / case_id
    intermediates_dir = case_dir / "intermediates"
    intermediates_dir.mkdir(parents=True, exist_ok=False)
    (case_dir / "gt.md").write_bytes(reference_bytes)
    (case_dir / "pred.raw.md").write_text(prediction, encoding="utf-8")
    write_json(intermediates_dir / "ocr.json", ocr)
    write_json(intermediates_dir / "formatted.json", formatted)


def publish_staged_output(staging_dir: Path, output_dir: Path) -> None:
    """Replace the last successful output, restoring it if publication fails."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    backup_dir = output_dir.parent / f".{output_dir.name}.previous-{uuid4().hex}"
    had_previous = output_dir.exists()

    if had_previous:
        os.replace(output_dir, backup_dir)

    published = False
    try:
        os.replace(staging_dir, output_dir)
        published = True
    finally:
        if not published and had_previous:
            os.replace(backup_dir, output_dir)

    if had_previous:
        shutil.rmtree(backup_dir)


@contextmanager
def staged_output(output_dir: Path) -> Iterator[Path]:
    """Yield an isolated build directory and publish it only on success."""
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.staging-", dir=output_dir.parent)
    )
    try:
        yield staging_dir
        publish_staged_output(staging_dir, output_dir)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)


__all__ = [
    "publish_staged_output",
    "staged_output",
    "write_case_artifacts",
    "write_json",
    "write_run_metadata",
]
