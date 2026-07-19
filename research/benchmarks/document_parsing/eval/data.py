"""Ground-truth dataset rows for MLflow dataset logging."""

from __future__ import annotations

from research.benchmarks.document_parsing.models import BenchmarkManifest


def build_ground_truth_dataset_rows(
    manifest: BenchmarkManifest,
    *,
    references: dict[str, bytes],
) -> list[dict[str, object]]:
    """One row per benchmark case with manifest metadata and reference Markdown."""
    expected_case_ids = {case.case_id for case in manifest.cases}
    if set(references) != expected_case_ids:
        raise ValueError("reference snapshot case IDs do not match manifest cases")

    rows: list[dict[str, object]] = []
    for case in sorted(manifest.cases, key=lambda item: item.case_id):
        rows.append(
            {
                "case_id": case.case_id,
                "data_source": case.data_source,
                "doc_type": case.doc_type,
                "technical_tags": case.technical_tags,
                "purpose": case.purpose,
                "input_path": case.input.path.as_posix(),
                "input_sha256": case.input.sha256,
                "reference_path": case.reference_path.as_posix(),
                "reference_markdown": references[case.case_id].decode("utf-8"),
            }
        )
    return rows


__all__ = ["build_ground_truth_dataset_rows"]
