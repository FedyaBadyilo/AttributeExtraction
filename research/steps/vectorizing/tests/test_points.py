from qdrant_client.http.models import PointStruct, SparseVector

from research.steps.chunking.domain.models import Chunk, StructureChunkMetadata
from research.steps.vectorizing.domain.points import (
    DENSE_VECTOR_NAME,
    SPARSE_VECTOR_NAME,
    build_point,
)


def test_build_point_uses_hybrid_vectors_and_global_point_id() -> None:
    chunk = Chunk(
        content="text",
        metadata=StructureChunkMetadata(document_chunk_index=0),
    )
    sparse_vec = SparseVector(indices=[1], values=[0.5])
    point = build_point(chunk, [0.1, 0.2], sparse_vec, point_id=42)

    assert point.id == 42
    assert point.vector[DENSE_VECTOR_NAME] == [0.1, 0.2]
    assert point.vector[SPARSE_VECTOR_NAME] == sparse_vec
    assert point.payload["content"] == "text"
    assert point.payload["metadata"]["document_chunk_index"] == 0
    assert isinstance(point, PointStruct)
