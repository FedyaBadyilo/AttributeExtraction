"""MLflow adapter for backend-independent Markdown scoring."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import ClassVar, Literal

import mlflow
import pandas as pd
from infra.research_eval.types import BaseEvalAdapter, EvalResult
from research.benchmarks.document_parsing.artifacts import staged_output
from research.benchmarks.document_parsing.canonicalize import canonicalize_pair
from research.benchmarks.document_parsing.eval.data import build_ground_truth_dataset_rows
from research.benchmarks.document_parsing.eval.models import (
    CaseArtifactPaths,
    CaseEvalRecord,
)
from research.benchmarks.document_parsing.eval.params import benchmark_params
from research.benchmarks.document_parsing.manifest import (
    DEFAULT_MANIFEST_PATH,
    REPOSITORY_ROOT,
    compute_dataset_digest_from_references,
)
from research.benchmarks.document_parsing.models import BenchmarkManifest
from research.benchmarks.document_parsing.scoring import (
    prediction_for_scoring,
    score_prepared_document,
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _load_snapshot(source_dir: Path) -> tuple[BenchmarkManifest, str, dict[str, bytes]]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"benchmark output directory not found: {source_dir}")

    manifest_path = source_dir / "manifest.snapshot.json"
    digest_path = source_dir / "dataset.digest"
    manifest = BenchmarkManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    dataset_digest = digest_path.read_text(encoding="ascii").strip()
    if not _DIGEST_RE.fullmatch(dataset_digest):
        raise ValueError(f"invalid dataset digest: {dataset_digest!r}")

    expected_case_ids = {case.case_id for case in manifest.cases}
    cases_dir = source_dir / "cases"
    actual_case_ids = {path.name for path in cases_dir.iterdir() if path.is_dir()}
    if actual_case_ids != expected_case_ids:
        raise ValueError(
            "snapshot case directories do not match manifest: "
            f"expected {sorted(expected_case_ids)}, got {sorted(actual_case_ids)}"
        )

    references: dict[str, bytes] = {}
    for case in manifest.cases:
        case_dir = cases_dir / case.case_id
        required_paths = (
            case_dir / "gt.md",
            case_dir / "intermediates/ocr.json",
            case_dir / "intermediates/formatted.json",
        )
        for path in required_paths:
            if not path.is_file():
                raise FileNotFoundError(
                    f"required snapshot file for {case.case_id} not found: {path}"
                )
        if not (
            (case_dir / "pred.raw.md").is_file()
            or (case_dir / "pred.canonical.md").is_file()
        ):
            raise FileNotFoundError(
                f"prediction for case {case.case_id} not found in {case_dir}"
            )
        references[case.case_id] = (case_dir / "gt.md").read_bytes()

    actual_digest = compute_dataset_digest_from_references(
        manifest, references=references
    )
    if actual_digest != dataset_digest:
        raise ValueError(
            "snapshot dataset digest mismatch: "
            f"expected {dataset_digest}, got {actual_digest}"
        )
    return manifest, dataset_digest, references


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _score_into_snapshot(
    source_dir: Path,
    manifest: BenchmarkManifest,
) -> list[CaseEvalRecord]:
    records: list[CaseEvalRecord] = []
    with staged_output(source_dir) as staging_dir:
        shutil.copytree(source_dir, staging_dir, dirs_exist_ok=True)

        for case in manifest.cases:
            case_dir = staging_dir / "cases" / case.case_id
            raw_path = case_dir / "pred.raw.md"
            existing_canonical_path = case_dir / "pred.canonical.md"
            prediction_path = raw_path if raw_path.is_file() else existing_canonical_path
            raw_prediction = prediction_path.read_text(encoding="utf-8")
            raw_ground_truth = (case_dir / "gt.md").read_text(encoding="utf-8")
            scoring_pred, table_parse_error = prediction_for_scoring(
                raw_prediction, raw_ground_truth
            )
            scores = score_prepared_document(
                scoring_pred,
                raw_ground_truth,
                table_parse_error=table_parse_error,
            )
            canonical_pred, canonical_gt = canonicalize_pair(
                scoring_pred, raw_ground_truth
            )

            canonical_pred_path = case_dir / "pred.canonical.md"
            canonical_gt_path = case_dir / "gt.canonical.md"
            canonical_pred_path.write_text(canonical_pred, encoding="utf-8")
            canonical_gt_path.write_text(canonical_gt, encoding="utf-8")
            if raw_path.is_file() and raw_prediction == canonical_pred:
                raw_path.unlink()

            records.append(
                CaseEvalRecord(
                    case_id=case.case_id,
                    data_source=case.data_source,
                    doc_type=case.doc_type,
                    technical_tags=case.technical_tags,
                    purpose=case.purpose,
                    scores=scores,
                    artifacts=CaseArtifactPaths(
                        gt=_relative(canonical_gt_path, staging_dir),
                        pred_canonical=_relative(canonical_pred_path, staging_dir),
                        pred_raw=(
                            _relative(raw_path, staging_dir) if raw_path.is_file() else None
                        ),
                        ocr=_relative(
                            case_dir / "intermediates/ocr.json", staging_dir
                        ),
                        formatted=_relative(
                            case_dir / "intermediates/formatted.json", staging_dir
                        ),
                    ),
                )
            )

        cases_path = staging_dir / "cases.jsonl"
        cases_path.write_text(
            "\n".join(
                json.dumps(record.model_dump(mode="json"), ensure_ascii=False)
                for record in records
            )
            + "\n",
            encoding="utf-8",
        )
    return records


def _macro_metrics(records: list[CaseEvalRecord]) -> dict[str, float]:
    if not records:
        raise ValueError("benchmark snapshot contains no cases")
    count = len(records)

    def mean(values: list[float]) -> float:
        return sum(values) / count

    return {
        "cer": mean([record.scores.text.cer for record in records]),
        "wer": mean([record.scores.text.wer for record in records]),
        "token_f1": mean([record.scores.text.token_f1 for record in records]),
        "teds": mean([record.scores.tables.teds for record in records]),
        "teds_s": mean(
            [record.scores.tables.teds_structure for record in records]
        ),
        "structural_counts_similarity": mean(
            [record.scores.structure.counts.similarity for record in records]
        ),
        "heading_sequence_f1": mean(
            [record.scores.structure.headings.f1 for record in records]
        ),
        "ast_structure_similarity": mean(
            [record.scores.structure.ast_similarity for record in records]
        ),
        "case_count": float(count),
        "table_parse_error_count": float(
            sum(record.scores.table_parse_error is not None for record in records)
        ),
    }


def _snapshot_artifacts(source_dir: Path) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for path in sorted(source_dir.rglob("*")):
        if path.is_file() and path.name != ".gitkeep":
            relative = path.relative_to(source_dir).as_posix()
            artifacts[f"snapshot/{relative}"] = path
    return artifacts


class DocumentParsingEvalAdapter(BaseEvalAdapter):
    target = "nsi-attribute-extraction-ocr"
    eval_mode: ClassVar[Literal["rebuild", "reuse"]] = "reuse"

    def __init__(self, *, config: dict | None = None) -> None:
        self._config = config

    def evaluate(self, source: str | Path) -> EvalResult:
        source_dir = Path(source).resolve()
        manifest, dataset_digest, references = _load_snapshot(source_dir)
        records = _score_into_snapshot(source_dir, manifest)
        mlflow.log_input(
            mlflow.data.from_pandas(
                pd.DataFrame(
                    build_ground_truth_dataset_rows(manifest, references=references)
                ),
                source=str(REPOSITORY_ROOT / DEFAULT_MANIFEST_PATH),
                name="document_parsing_ground_truth",
            ),
            context="eval",
        )
        return EvalResult(
            metrics=_macro_metrics(records),
            params=benchmark_params(
                dataset_digest=dataset_digest,
                manifest_schema_version=manifest.schema_version,
                eval_mode=self.eval_mode,
                config=self._config,
            ),
            artifacts=_snapshot_artifacts(source_dir),
        )


class RebuildDocumentParsingEvalAdapter(DocumentParsingEvalAdapter):
    eval_mode = "rebuild"


__all__ = [
    "DocumentParsingEvalAdapter",
    "RebuildDocumentParsingEvalAdapter",
]
