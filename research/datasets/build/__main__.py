from __future__ import annotations

import argparse
from pathlib import Path

from infra.config.loader import _project_root
from research.datasets.build.builder import build_dataset

DEFAULT_OUTPUT = _project_root / "research/datasets/processed"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build processed dataset artifacts from nci and PDF manifest.")
    parser.add_argument(
        "--pdf-registry-path",
        type=Path,
        required=True,
        help="Path to pdf_files_manifest.xlsx",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for processed artifacts",
    )
    args = parser.parse_args()

    build_dataset(
        manifest_path=args.pdf_registry_path.resolve(),
        output_dir=args.output_dir.resolve(),
    )


if __name__ == "__main__":
    main()
