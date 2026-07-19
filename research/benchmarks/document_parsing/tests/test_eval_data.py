from __future__ import annotations

import hashlib

from research.benchmarks.document_parsing.eval.data import build_ground_truth_dataset_rows
from research.benchmarks.document_parsing.models import BenchmarkManifest


def _manifest() -> BenchmarkManifest:
    return BenchmarkManifest.model_validate(
        {
            "schema_version": 1,
            "cases": [
                {
                    "case_id": "case-b",
                    "data_source": "synthetic",
                    "doc_type": "test",
                    "technical_tags": ["offline"],
                    "purpose": "second case",
                    "source": {
                        "path": "source-b.pdf",
                        "page_ranges": [{"start": 1, "end": 1}],
                    },
                    "transformations": [],
                    "input": {
                        "path": "input-b.pdf",
                        "sha256": hashlib.sha256(b"b").hexdigest(),
                    },
                    "reference_path": "reference-b.md",
                },
                {
                    "case_id": "case-a",
                    "data_source": "synthetic",
                    "doc_type": "test",
                    "technical_tags": ["offline", "table"],
                    "purpose": "first case",
                    "source": {
                        "path": "source-a.pdf",
                        "page_ranges": [{"start": 1, "end": 2}],
                    },
                    "transformations": [],
                    "input": {
                        "path": "input-a.pdf",
                        "sha256": hashlib.sha256(b"a").hexdigest(),
                    },
                    "reference_path": "reference-a.md",
                },
            ],
        }
    )


def test_build_ground_truth_dataset_rows_are_sorted_and_include_reference_markdown() -> None:
    manifest = _manifest()
    rows = build_ground_truth_dataset_rows(
        manifest,
        references={
            "case-a": b"# A",
            "case-b": b"# B",
        },
    )

    assert [row["case_id"] for row in rows] == ["case-a", "case-b"]
    assert rows[0]["reference_markdown"] == "# A"
    assert rows[0]["technical_tags"] == ["offline", "table"]
    assert rows[1]["input_sha256"] == hashlib.sha256(b"b").hexdigest()
