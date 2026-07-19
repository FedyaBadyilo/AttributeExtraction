"""Embed chunks and upsert into Qdrant (one collection per eos_id)."""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient

from infra.qdrant import get_qdrant_client
from research.steps.chunking.domain.models import Chunk
from research.steps.vectorizing.domain.collection import ensure_collection
from research.steps.vectorizing.domain.dense_embed import embed_dense_texts
from research.steps.vectorizing.domain.points import build_point
from research.steps.vectorizing.domain.prepare import prepare_content_for_indexing
from research.steps.vectorizing.domain.sparse_embed import embed_sparse_documents
from research.steps.vectorizing.domain.upsert import upsert_points

logger = logging.getLogger(__name__)


def index_chunks(
    items: list[Chunk],
    config: dict[str, Any],
    collection_name: str,
    *,
    qdrant: QdrantClient | None = None,
    recreate_collection: bool = True,
) -> int:
    """Embed chunks, (re)create collection, upsert points. Returns number of points upserted."""
    if not items:
        return 0

    enriched = [
        prepare_content_for_indexing(chunk.content, chunk.metadata.header_path)
        for chunk in items
    ]

    dense_vectors = embed_dense_texts(enriched, config)
    vector_size = len(dense_vectors[0])
    logger.info("Embedded %d texts, vector size %d", len(dense_vectors), vector_size)

    qdrant = qdrant or get_qdrant_client(config)
    ensure_collection(
        qdrant,
        collection_name,
        vector_size=vector_size,
        recreate=recreate_collection,
    )

    sparse_vectors = embed_sparse_documents(enriched)
    points = [
        build_point(chunk, dense_vector, sparse_vector, point_id=point_id)
        for point_id, (chunk, dense_vector, sparse_vector) in enumerate(
            zip(items, dense_vectors, sparse_vectors)
        )
    ]
    upsert_points(qdrant, collection_name, points)
    logger.info("Upserted %d points to collection %s", len(points), collection_name)
    return len(points)
