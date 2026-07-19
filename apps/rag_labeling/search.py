"""Vector search for RAG labeling via retrieval step hybrid search."""

from __future__ import annotations

from typing import Any

from infra.qdrant import get_qdrant_client
from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.retrieval.domain.query import build_search_query
from research.steps.retrieval.domain.search.runner import (
    _embed_dense_queries,
    _hybrid_search,
)
from research.steps.vectorizing.domain.sparse_embed import embed_sparse_queries


def search_candidates(
    config: dict[str, Any],
    collection_name: str,
    attr: ClassAttribute,
    *,
    execution_variant: str | None = None,
    reference_value: str,
    limit: int = 10,
) -> list[dict]:
    """Top-k hybrid hits for one attribute (production query + эталон suffix)."""
    base = build_search_query(attr, execution_variant=execution_variant)
    if not base:
        return []

    query = f"{base} | эталон: {reference_value}"
    step_cfg = config["RETRIEVAL"]
    pf_dense = int(step_cfg["prefetch_limit_dense"])
    pf_bm25 = int(step_cfg["prefetch_limit_bm25"])

    qdrant = get_qdrant_client(config)
    dense_vector = _embed_dense_queries([query], config)[0]
    sparse_vector = embed_sparse_queries([query])[0]
    hits = _hybrid_search(
        qdrant,
        collection_name,
        limit=limit,
        prefetch_limit_dense=pf_dense,
        prefetch_limit_bm25=pf_bm25,
        dense_vector=dense_vector,
        sparse_vector=sparse_vector,
    )

    return [
        {
            "id": hit.id,
            "score": hit.score,
            "payload": {
                "content": hit.payload.content,
                "metadata": hit.payload.metadata.model_dump(mode="json"),
            },
        }
        for hit in hits
    ]
