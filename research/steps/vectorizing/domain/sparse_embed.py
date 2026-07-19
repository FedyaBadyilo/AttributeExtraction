"""Client-side BM25 sparse vectors (Qdrant server has no InferenceService)."""

from __future__ import annotations

from functools import lru_cache

from qdrant_client.http.models import SparseVector

BM25_MODEL = "Qdrant/bm25"
BM25_LANGUAGE = "russian"
BM25_BATCH_SIZE = 32


@lru_cache(maxsize=1)
def _bm25_embedder():
    from fastembed import SparseTextEmbedding

    return SparseTextEmbedding(model_name=BM25_MODEL, language=BM25_LANGUAGE)


def _to_sparse_vector(embedding) -> SparseVector:
    return SparseVector(
        indices=embedding.indices.tolist(),
        values=embedding.values.tolist(),
    )


def embed_sparse_documents(texts: list[str]) -> list[SparseVector]:
    """BM25 document vectors (TF-weighted) for indexing."""
    if not texts:
        return []
    embedder = _bm25_embedder()
    return [
        _to_sparse_vector(embedding)
        for embedding in embedder.embed(texts, batch_size=BM25_BATCH_SIZE)
    ]


def embed_sparse_queries(texts: list[str]) -> list[SparseVector]:
    """BM25 query vectors (binary weights) for hybrid retrieval."""
    if not texts:
        return []
    embedder = _bm25_embedder()
    return [_to_sparse_vector(embedding) for embedding in embedder.query_embed(texts)]
