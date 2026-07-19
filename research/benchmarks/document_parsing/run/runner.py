"""Filesystem orchestration for the dedoc-only benchmark build."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable

from infra.config.loader import get_config_and_env
from research.benchmarks.document_parsing.artifacts import (
    staged_output,
    write_case_artifacts,
    write_run_metadata,
)
from research.benchmarks.document_parsing.manifest import (
    DEFAULT_MANIFEST_PATH,
    REPOSITORY_ROOT,
    compute_dataset_digest,
    load_manifest,
    resolve_repo_path,
)
from research.benchmarks.document_parsing.pipelines.dedoc import run_dedoc_pipeline
from research.steps.markdown_formatting.domain.models import FormattedDocument

DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "research/benchmarks/document_parsing/output"


def run_benchmark(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    repo_root: Path = REPOSITORY_ROOT,
    config: dict[str, Any] | None = None,
    converter: Callable[..., Any] | None = None,
    formatter: Callable[[Any], FormattedDocument] | None = None,
) -> str:
    """Build and publish one complete benchmark artifact snapshot."""
    manifest = load_manifest(manifest_path, repo_root=repo_root)
    dataset_digest = compute_dataset_digest(manifest, repo_root=repo_root)
    pipeline_config = get_config_and_env() if config is None else config

    with staged_output(output_dir) as staging_dir:
        write_run_metadata(
            staging_dir,
            manifest=manifest,
            dataset_digest=dataset_digest,
        )
        work_root = staging_dir / ".work"

        for case in manifest.cases:
            parsed, formatted, prediction = run_dedoc_pipeline(
                resolve_repo_path(repo_root, case.input.path),
                work_root / case.case_id,
                config=pipeline_config,
                converter=converter,
                formatter=formatter,
            )
            write_case_artifacts(
                staging_dir,
                case_id=case.case_id,
                reference_bytes=resolve_repo_path(
                    repo_root, case.reference_path
                ).read_bytes(),
                prediction=prediction,
                ocr=parsed.model_dump(mode="json"),
                formatted=formatted.model_dump(mode="json"),
            )

        if work_root.exists():
            shutil.rmtree(work_root)

    return dataset_digest


__all__ = ["DEFAULT_OUTPUT_DIR", "run_benchmark"]
