from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from research.benchmarks.document_parsing.manifest import (
    compute_dataset_digest,
    load_manifest,
)
from research.benchmarks.document_parsing.models import BenchmarkManifest


def _write_case_files(root: Path, name: str, *, reference: bytes = b"reference") -> dict:
    source = root / f"source-{name}.pdf"
    input_path = root / f"input-{name}.pdf"
    reference_path = root / f"reference-{name}.md"
    source.write_bytes(b"source")
    input_path.write_bytes(f"input-{name}".encode())
    reference_path.write_bytes(reference)
    return {
        "case_id": name,
        "data_source": "synthetic",
        "doc_type": "test",
        "technical_tags": ["offline"],
        "purpose": f"offline fixture {name}",
        "source": {
            "path": source.relative_to(root).as_posix(),
            "page_ranges": [{"start": 1, "end": 2}],
        },
        "transformations": [],
        "input": {
            "path": input_path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        },
        "reference_path": reference_path.relative_to(root).as_posix(),
    }


def _write_manifest(root: Path, cases: list[dict], **extra: object) -> Path:
    path = root / "manifest.json"
    path.write_text(
        json.dumps({"schema_version": 1, "cases": cases, **extra}),
        encoding="utf-8",
    )
    return path


def test_load_manifest_preflights_paths_and_input_sha(tmp_path: Path) -> None:
    case = _write_case_files(tmp_path, "case-a")
    manifest = load_manifest(_write_manifest(tmp_path, [case]), repo_root=tmp_path)
    assert manifest.cases[0].case_id == "case-a"

    (tmp_path / case["input"]["path"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="sha256 mismatch"):
        load_manifest(tmp_path / "manifest.json", repo_root=tmp_path)


def test_manifest_forbids_extra_fields_at_every_level(tmp_path: Path) -> None:
    case = _write_case_files(tmp_path, "case-a")
    case["source"]["unexpected"] = True
    with pytest.raises(ValidationError, match="extra_forbidden"):
        BenchmarkManifest.model_validate({"schema_version": 1, "cases": [case]})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source", {"path": "../outside.pdf", "page_ranges": [{"start": 1, "end": 1}]}, "repository-relative"),
        ("source", {"path": "source.pdf", "page_ranges": [{"start": 0, "end": 1}]}, "greater than or equal"),
        ("source", {"path": "source.pdf", "page_ranges": [{"start": 3, "end": 2}]}, "page range end"),
    ],
)
def test_manifest_rejects_invalid_paths_and_page_ranges(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    case = _write_case_files(tmp_path, "case-a")
    case[field] = value
    with pytest.raises(ValidationError, match=message):
        BenchmarkManifest.model_validate({"schema_version": 1, "cases": [case]})


def test_manifest_requires_unique_case_and_source_selection(tmp_path: Path) -> None:
    case = _write_case_files(tmp_path, "case-a")
    duplicate_id = deepcopy(case)
    duplicate_id["source"]["page_ranges"] = [{"start": 3, "end": 3}]
    with pytest.raises(ValidationError, match="duplicate case_id"):
        BenchmarkManifest.model_validate(
            {"schema_version": 1, "cases": [case, duplicate_id]}
        )

    duplicate_source = deepcopy(case)
    duplicate_source["case_id"] = "case-b"
    with pytest.raises(ValidationError, match="duplicate source path and page ranges"):
        BenchmarkManifest.model_validate(
            {"schema_version": 1, "cases": [case, duplicate_source]}
        )


def test_load_manifest_requires_every_referenced_file(tmp_path: Path) -> None:
    case = _write_case_files(tmp_path, "case-a")
    (tmp_path / case["reference_path"]).unlink()
    manifest_path = _write_manifest(tmp_path, [case])
    with pytest.raises(FileNotFoundError, match="reference file"):
        load_manifest(manifest_path, repo_root=tmp_path)


def test_dataset_digest_is_order_independent_and_includes_reference_bytes(
    tmp_path: Path,
) -> None:
    case_a = _write_case_files(tmp_path, "case-a", reference=b"alpha")
    case_b = _write_case_files(tmp_path, "case-b", reference=b"beta")
    first = BenchmarkManifest.model_validate(
        {"schema_version": 1, "cases": [case_a, case_b]}
    )
    reversed_manifest = BenchmarkManifest.model_validate(
        {"schema_version": 1, "cases": [case_b, case_a]}
    )

    original_digest = compute_dataset_digest(first, repo_root=tmp_path)
    assert original_digest == compute_dataset_digest(
        reversed_manifest, repo_root=tmp_path
    )

    (tmp_path / case_a["reference_path"]).write_bytes(b"changed")
    assert original_digest != compute_dataset_digest(first, repo_root=tmp_path)
