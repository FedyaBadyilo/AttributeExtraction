"""FormattedDocument → ChunkedDocument conversion."""

from __future__ import annotations

from infra.config import get_config_and_env
from research.steps.chunking.domain.build import build_chunks
from research.steps.chunking.domain.models import ChunkedDocument
from research.steps.chunking.domain.splitters import make_token_count_fn
from research.steps.markdown_formatting.domain.models import FormattedDocument


def chunk_document(
    document: FormattedDocument,
    *,
    eos_id: int,
    pdf_filename: str,
    config: dict | None = None,
) -> ChunkedDocument:
    """Build chunks from a formatted markdown document."""
    config = config or get_config_and_env()
    chunking_cfg = config["CHUNKING"]
    embedder_key: str = chunking_cfg["embedder_model_key"]
    embedder_cfg = config["EMBEDDINGS"][embedder_key]

    token_count_fn = make_token_count_fn(embedder_cfg["model"])
    chunks = build_chunks(
        document,
        max_chunk_tokens=int(chunking_cfg["max_chunk_tokens"]),
        min_chunk_tokens=int(chunking_cfg["min_chunk_tokens"]),
        token_count_fn=token_count_fn,
        file_name=pdf_filename,
    )
    return ChunkedDocument(eos_id=eos_id, pdf_filename=pdf_filename, chunks=chunks)
