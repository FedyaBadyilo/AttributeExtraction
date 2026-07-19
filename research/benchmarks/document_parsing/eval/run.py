"""Rebuild or reuse benchmark output, then log one MLflow evaluation run."""

from __future__ import annotations

import argparse
from pathlib import Path

from infra.config import config_logger
from infra.research_eval.runner import evaluate_experiment
from research.benchmarks.document_parsing.eval.adapter import (
    DocumentParsingEvalAdapter,
    RebuildDocumentParsingEvalAdapter,
)
from research.benchmarks.document_parsing.manifest import (
    DEFAULT_MANIFEST_PATH,
    REPOSITORY_ROOT,
)
from research.benchmarks.document_parsing.run.runner import run_benchmark


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--mode", required=True, choices=("rebuild", "reuse"))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Used only in rebuild mode",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="Repository root used to resolve manifest paths",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    source = args.source.resolve()
    if args.mode == "rebuild":
        run_benchmark(
            manifest_path=args.manifest,
            output_dir=source,
            repo_root=args.repo_root,
        )
        adapter_cls = RebuildDocumentParsingEvalAdapter
    else:
        adapter_cls = DocumentParsingEvalAdapter

    evaluate_experiment(
        adapter_cls=adapter_cls,
        source=source,
        name=args.name,
    )


if __name__ == "__main__":
    config_logger()
    main()
