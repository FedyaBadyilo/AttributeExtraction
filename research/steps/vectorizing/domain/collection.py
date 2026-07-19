"""Qdrant collection setup for hybrid dense + sparse indexing."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, Modifier, SparseVectorParams, VectorParams

from research.steps.vectorizing.domain.points import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    *,
    vector_size: int,
    recreate: bool = True,
) -> None:
    """Create or recreate the hybrid dense + BM25 collection."""
    vectors_config = {
        DENSE_VECTOR_NAME: VectorParams(size=vector_size, distance=Distance.COSINE),
    }
    sparse_config = {
        SPARSE_VECTOR_NAME: SparseVectorParams(modifier=Modifier.IDF),
    }
    if recreate:
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=vectors_config,
            sparse_vectors_config=sparse_config,
        )
        return

    if client.collection_exists(collection_name):
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=vectors_config,
        sparse_vectors_config=sparse_config,
    )
