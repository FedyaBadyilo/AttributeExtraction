"""Entrypoint: chunk markdown_formatting artifacts into retrieval-ready chunks.

Usage:
    python -m research.steps.chunking.run
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from infra.config.loader import config_logger
from research.datasets.access import load_examples_manifest
from research.steps.chunking.domain import chunk_document
from research.steps.ocr.domain.models import SourceFile
from research.steps.markdown_formatting.domain.models import FormattedDocument

logger = logging.getLogger(__name__)

MARKDOWN_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "markdown_formatting" / "output"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def main() -> None:
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]
    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(source_files)
    for i, sf in enumerate(source_files, start=1):
        eos_id = sf.eos_id
        pdf_filename = sf.pdf_filename
        stem = Path(pdf_filename).stem
        markdown_path = MARKDOWN_OUTPUT_DIR / f"{stem}.json"
        logger.info("[%d/%d] eos_id=%s  file=%s", i, total, eos_id, pdf_filename)

        if not markdown_path.exists():
            raise FileNotFoundError(f"markdown_formatting output not found: {markdown_path}")

        document = FormattedDocument.model_validate(
            json.loads(markdown_path.read_text(encoding="utf-8"))
        )
        result = chunk_document(document, eos_id=eos_id, pdf_filename=pdf_filename)

        out_path = out_dir / f"{stem}.json"
        out_path.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved %d chunks -> %s", len(result.chunks), out_path)


if __name__ == "__main__":
    config_logger()
    main()
