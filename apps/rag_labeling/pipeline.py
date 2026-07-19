"""On-demand OCR → markdown → chunking → vectorizing for one eos_id."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research.datasets.access import RAW_PDF_DIR
from research.steps.chunking.domain import chunk_document
from research.steps.chunking.domain.models import Chunk
from research.steps.markdown_formatting.domain import format_document
from research.steps.ocr.domain import convert_document
from research.steps.vectorizing.domain import index_chunks

from apps.rag_labeling.config_paths import RAG_PIPELINE_CACHE_DIR, get_source_files_for_eos

_INDEXED_FILE = RAG_PIPELINE_CACHE_DIR / "indexed.json"
QDRANT_COLLECTION_TEMPLATE_RAG = "RAG-Labeling-{eos_id}"


def _load_indexed() -> set[int]:
    if not _INDEXED_FILE.exists():
        return set()
    with open(_INDEXED_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return {int(eid) for eid in data["eos_ids"]}


def _save_indexed(eos_ids: set[int]) -> None:
    RAG_PIPELINE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_INDEXED_FILE, "w", encoding="utf-8") as f:
        json.dump({"eos_ids": sorted(eos_ids)}, f, ensure_ascii=False)


def mark_not_indexed(eos_id: int) -> None:
    """Remove eos_id from the persistent indexed cache."""
    indexed = _load_indexed()
    if eos_id not in indexed:
        return
    indexed.discard(eos_id)
    _save_indexed(indexed)


def ensure_indexed(eos_id: int, config: dict[str, Any], *, force: bool = False) -> None:
    """
    Run ocr → markdown_formatting → chunking → vectorizing for eos_id if not yet done.
    Uses persistent cache; delete RAG_PIPELINE_CACHE_DIR to re-index all documents.
    """
    indexed = _load_indexed()
    if (not force) and (eos_id in indexed):
        return

    if force and eos_id in indexed:
        indexed.discard(eos_id)

    cache_dir = RAG_PIPELINE_CACHE_DIR / str(eos_id)
    cache_dir.mkdir(parents=True, exist_ok=True)

    all_chunks: list[Chunk] = []
    for sf in get_source_files_for_eos(eos_id):
        pdf_path = RAW_PDF_DIR / sf.pdf_filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        stem = Path(sf.pdf_filename).stem
        ocr_dir = cache_dir / "ocr" / stem
        parsed = convert_document(
            file_path=pdf_path,
            output_dir=ocr_dir,
            config=config,
            attachments_subdir=stem,
        )
        formatted = format_document(parsed.content)
        document = chunk_document(
            formatted,
            eos_id=eos_id,
            pdf_filename=sf.pdf_filename,
            config=config,
        )
        all_chunks.extend(document.chunks)

    collection_name = QDRANT_COLLECTION_TEMPLATE_RAG.format(eos_id=eos_id)
    if not all_chunks:
        raise ValueError(f"No chunks produced for eos_id={eos_id}")

    index_chunks(all_chunks, config, collection_name)

    indexed.add(eos_id)
    _save_indexed(indexed)
