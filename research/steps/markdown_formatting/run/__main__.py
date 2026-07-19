"""Entrypoint: format OCR ParsedDocument JSON artifacts to markdown trees.

Usage:
    python -m research.steps.markdown_formatting.run
"""

import json
import logging
from pathlib import Path

from dedoc.api.schema.parsed_document import ParsedDocument

from infra.config.loader import config_logger
from research.datasets.access import load_examples_manifest
from research.steps.markdown_formatting.domain import format_document
from research.steps.ocr.domain.models import SourceFile

logger = logging.getLogger(__name__)

OCR_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "ocr" / "output"
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
        ocr_path = OCR_OUTPUT_DIR / f"{stem}.json"
        logger.info("[%d/%d] eos_id=%s  file=%s", i, total, eos_id, pdf_filename)

        if not ocr_path.exists():
            raise FileNotFoundError(f"OCR output not found: {ocr_path}")

        parsed = ParsedDocument.model_validate(json.loads(ocr_path.read_text(encoding="utf-8")))
        result = format_document(parsed.content)

        out_path = out_dir / f"{stem}.json"
        out_path.write_text(
            json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved -> %s", out_path)


if __name__ == "__main__":
    config_logger()
    main()
