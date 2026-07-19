from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.benchmarks.document_parsing.artifacts import (
    staged_output,
    write_case_artifacts,
    write_run_metadata,
)
from research.benchmarks.document_parsing.models import BenchmarkManifest


def _manifest() -> BenchmarkManifest:
    return BenchmarkManifest.model_validate(
        {
            "schema_version": 1,
            "cases": [
                {
                    "case_id": "case-a",
                    "data_source": "synthetic",
                    "doc_type": "test",
                    "technical_tags": [],
                    "purpose": "offline artifacts fixture",
                    "source": {
                        "path": "source.pdf",
                        "page_ranges": [{"start": 1, "end": 1}],
                    },
                    "transformations": [],
                    "input": {"path": "input.pdf", "sha256": "a" * 64},
                    "reference_path": "reference.md",
                }
            ],
        }
    )


def test_staging_failure_preserves_last_successful_output(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "marker").write_text("old", encoding="utf-8")

    with pytest.raises(RuntimeError, match="case failed"):
        with staged_output(output) as staging:
            (staging / "partial").write_text("partial", encoding="utf-8")
            raise RuntimeError("case failed")

    assert (output / "marker").read_text(encoding="utf-8") == "old"
    assert not (output / "partial").exists()
    assert list(tmp_path.glob(".output.staging-*")) == []


def test_success_replaces_output_and_writes_required_layout(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "obsolete").write_text("old", encoding="utf-8")

    with staged_output(output) as staging:
        write_run_metadata(staging, manifest=_manifest(), dataset_digest="d" * 64)
        write_case_artifacts(
            staging,
            case_id="case-a",
            reference_bytes=b"ground truth\n",
            prediction="prediction\n",
            ocr={"content": {}},
            formatted={"structure": {}, "tables": []},
        )

    assert not (output / "obsolete").exists()
    assert (output / "dataset.digest").read_text(encoding="ascii") == "d" * 64 + "\n"
    snapshot = json.loads(
        (output / "manifest.snapshot.json").read_text(encoding="utf-8")
    )
    assert snapshot["schema_version"] == 1
    assert (output / "cases/case-a/gt.md").read_bytes() == b"ground truth\n"
    assert (output / "cases/case-a/pred.raw.md").read_text() == "prediction\n"
    assert json.loads(
        (output / "cases/case-a/intermediates/ocr.json").read_text()
    ) == {"content": {}}
    assert json.loads(
        (output / "cases/case-a/intermediates/formatted.json").read_text()
    ) == {"structure": {}, "tables": []}
