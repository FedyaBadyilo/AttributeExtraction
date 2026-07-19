"""Dense embedding for chunk indexing."""

from __future__ import annotations

from typing import Any

from infra.llm.embeddings import get_openai_embeddings

EMBED_CHUNK_SIZE = 64


def embed_dense_texts(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    """Embed texts with the configured dense model."""
    if not texts:
        return []
    embedder_key: str = config["VECTORIZING"]["embedder_model_key"]
    embedder = get_openai_embeddings(embedder_key, config)
    return embedder.embed_documents(texts, chunk_size=EMBED_CHUNK_SIZE)
