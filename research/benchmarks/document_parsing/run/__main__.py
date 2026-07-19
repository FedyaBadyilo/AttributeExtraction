"""Bench-only CLI for rebuilding Document Parsing Benchmark artifacts."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from infra.config.loader import config_logger
from research.benchmarks.document_parsing.manifest import (
    DEFAULT_MANIFEST_PATH,
    REPOSITORY_ROOT,
)
from research.benchmarks.document_parsing.run.runner import (
    DEFAULT_OUTPUT_DIR,
    run_benchmark,
)

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Manifest path, relative to --repo-root unless absolute",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory containing only the latest successful run",
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
    digest = run_benchmark(
        manifest_path=args.manifest,
        output_dir=args.output_dir,
        repo_root=args.repo_root,
    )
    logger.info("Published benchmark output to %s (dataset %s)", args.output_dir, digest)


if __name__ == "__main__":
    config_logger()
    main()
