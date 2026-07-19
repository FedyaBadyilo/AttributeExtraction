"""Build Qdrant points from chunks and hybrid vectors."""

from __future__ import annotations

from typing import Any

from qdrant_client.http.models import PointStruct, SparseVector

from research.steps.chunking.domain.models import Chunk

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "bm25"


def point_payload(chunk: Chunk) -> dict[str, Any]:
    """Payload stored alongside dense and sparse vectors."""
    return {
        "content": chunk.content,
        "metadata": chunk.metadata.model_dump(),
    }


def build_point(
    chunk: Chunk,
    dense_vector: list[float],
    sparse_vector: SparseVector,
    *,
    point_id: int,
) -> PointStruct:
    """Build one Qdrant point from a chunk and its hybrid vectors."""
    return PointStruct(
        id=point_id,
        vector={
            DENSE_VECTOR_NAME: dense_vector,
            SPARSE_VECTOR_NAME: sparse_vector,
        },
        payload=point_payload(chunk),
    )
