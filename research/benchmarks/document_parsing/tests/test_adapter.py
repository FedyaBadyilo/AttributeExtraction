from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from research.benchmarks.document_parsing.artifacts import (
    write_case_artifacts,
    write_run_metadata,
)
from research.benchmarks.document_parsing.eval.adapter import (
    DocumentParsingEvalAdapter,
    RebuildDocumentParsingEvalAdapter,
)
from research.benchmarks.document_parsing.manifest import (
    compute_dataset_digest_from_references,
)
from research.benchmarks.document_parsing.models import BenchmarkManifest


def _snapshot(tmp_path: Path) -> Path:
    reference = b"# Title\n\nBody"
    input_bytes = b"input"
    manifest = BenchmarkManifest.model_validate(
        {
            "schema_version": 1,
            "cases": [
                {
                    "case_id": "case-a",
                    "data_source": "synthetic",
                    "doc_type": "test",
                    "technical_tags": ["offline"],
                    "purpose": "offline adapter fixture",
                    "source": {
                        "path": "source.pdf",
                        "page_ranges": [{"start": 1, "end": 1}],
                    },
                    "transformations": [],
                    "input": {
                        "path": "input.pdf",
                        "sha256": hashlib.sha256(input_bytes).hexdigest(),
                    },
                    "reference_path": "reference.md",
                }
            ],
        }
    )
    digest = compute_dataset_digest_from_references(
        manifest, references={"case-a": reference}
    )
    output = tmp_path / "output"
    output.mkdir()
    write_run_metadata(output, manifest=manifest, dataset_digest=digest)
    write_case_artifacts(
        output,
        case_id="case-a",
        reference_bytes=reference,
        prediction=reference.decode(),
        ocr={"content": {"structure": {}}},
        formatted={"structure": {}, "tables": []},
    )
    return output


def test_adapter_scores_snapshot_and_materializes_minimal_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _snapshot(tmp_path)
    logged: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        "research.benchmarks.document_parsing.eval.adapter.mlflow.log_input",
        lambda *args, **kwargs: logged.append((args, kwargs)),
    )
    result = DocumentParsingEvalAdapter(
        config={"OCR": {"on_gpu": False}}
    ).evaluate(output)

    assert result.metrics["cer"] == 1.0
    assert result.metrics["teds"] == 1.0
    assert result.metrics["ast_structure_similarity"] == 1.0
    assert result.metrics["case_count"] == 1.0
    assert result.params["eval_mode"] == "reuse"
    assert result.params["OCR.on_gpu"] == "False"
    assert "snapshot/cases.jsonl" in result.artifacts
    assert "snapshot/cases/case-a/gt.canonical.md" in result.artifacts
    assert "snapshot/cases/case-a/pred.canonical.md" in result.artifacts
    assert "snapshot/cases/case-a/pred.raw.md" not in result.artifacts

    rows = [
        json.loads(line)
        for line in (output / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["case_id"] == "case-a"
    assert rows[0]["technical_tags"] == ["offline"]
    assert rows[0]["purpose"] == "offline adapter fixture"
    assert rows[0]["artifacts"]["pred_raw"] is None
    assert len(logged) == 1
    assert logged[0][1]["context"] == "eval"


def test_rebuild_adapter_marks_mode_without_changing_scoring(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = _snapshot(tmp_path)
    monkeypatch.setattr(
        "research.benchmarks.document_parsing.eval.adapter.mlflow.log_input",
        lambda *args, **kwargs: None,
    )

    result = RebuildDocumentParsingEvalAdapter(
        config={"OCR": {"on_gpu": True}}
    ).evaluate(output)

    assert result.params["eval_mode"] == "rebuild"


def test_adapter_rejects_tampered_reference_snapshot(tmp_path: Path) -> None:
    output = _snapshot(tmp_path)
    (output / "cases/case-a/gt.md").write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="dataset digest mismatch"):
        DocumentParsingEvalAdapter(config={"OCR": {"on_gpu": False}}).evaluate(output)
