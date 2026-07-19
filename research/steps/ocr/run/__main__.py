"""Entrypoint: OCR all PDFs from examples_manifest.json.

Usage:
    python -m research.steps.ocr.run
"""
import json
import logging
from pathlib import Path

from infra.config.loader import config_logger, get_config_and_env
from research.datasets.access import RAW_PDF_DIR, load_examples_manifest
from research.steps.ocr.domain import convert_document
from research.steps.ocr.domain.models import SourceFile

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"


def main() -> None:
    config = get_config_and_env()
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]
    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(source_files)
    for i, sf in enumerate(source_files, start=1):
        eos_id = sf.eos_id
        pdf_filename = sf.pdf_filename
        pdf_path = RAW_PDF_DIR / pdf_filename
        logger.info("[%d/%d] eos_id=%s  file=%s", i, total, eos_id, pdf_filename)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        result = convert_document(
            file_path=pdf_path,
            output_dir=out_dir,
            config=config,
            attachments_subdir=pdf_path.stem,
        )

        out_path = out_dir / f"{pdf_path.stem}.json"
        out_path.write_text(
            json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Saved -> %s", out_path)


if __name__ == "__main__":
    config_logger()
    main()
