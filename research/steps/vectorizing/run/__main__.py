"""Entrypoint: index chunking artifacts into Qdrant (one collection per eos_id).

Usage:
    python -m research.steps.vectorizing.run
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from infra.config import get_config_and_env
from infra.config.loader import config_logger
from research.datasets.access import load_examples_manifest
from research.steps.chunking.domain.models import Chunk, ChunkedDocument
from research.steps.ocr.domain.models import SourceFile
from research.steps.vectorizing.domain import index_chunks

logger = logging.getLogger(__name__)

CHUNKING_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "chunking" / "output"


def main() -> None:
    config = get_config_and_env()
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]
    chunking_dir = CHUNKING_OUTPUT_DIR

    by_eos_id: dict[int, list[SourceFile]] = defaultdict(list)
    for sf in source_files:
        by_eos_id[sf.eos_id].append(sf)

    manifest_stems = {Path(sf.pdf_filename).stem for sf in source_files}
    eos_ids = sorted(by_eos_id)
    total_eos = len(eos_ids)
    for i, eos_id in enumerate(eos_ids, start=1):
        entries = by_eos_id[eos_id]
        items: list[Chunk] = []

        for sf in entries:
            pdf_filename = sf.pdf_filename
            stem = Path(pdf_filename).stem
            chunk_path = chunking_dir / f"{stem}.json"
            if not chunk_path.exists():
                raise FileNotFoundError(f"chunking output not found: {chunk_path}")

            document = ChunkedDocument.model_validate(
                json.loads(chunk_path.read_text(encoding="utf-8"))
            )
            if document.eos_id != eos_id:
                raise ValueError(
                    f"eos_id mismatch in {chunk_path}: manifest={eos_id}, artifact={document.eos_id}"
                )
            if document.pdf_filename != pdf_filename:
                raise ValueError(
                    f"pdf_filename mismatch in {chunk_path}: "
                    f"manifest={pdf_filename!r}, artifact={document.pdf_filename!r}"
                )

            items.extend(document.chunks)

        collection_name = config["QDRANT_COLLECTION_TEMPLATE"].format(eos_id=eos_id)
        logger.info(
            "[%d/%d] eos_id=%s  files=%d  chunks=%d  collection=%s",
            i,
            total_eos,
            eos_id,
            len(entries),
            len(items),
            collection_name,
        )
        if not items:
            logger.warning("[%d/%d] eos_id=%s  no chunks to index, skipping", i, total_eos, eos_id)
            continue

        index_chunks(items, config, collection_name)


if __name__ == "__main__":
    config_logger()
    main()
