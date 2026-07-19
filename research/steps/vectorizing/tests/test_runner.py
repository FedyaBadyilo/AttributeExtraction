from unittest.mock import MagicMock, patch

from research.steps.chunking.domain.models import Chunk, StructureChunkMetadata
from research.steps.vectorizing.domain.runner import index_chunks


@patch("research.steps.vectorizing.domain.runner.embed_sparse_documents")
@patch("research.steps.vectorizing.domain.runner.build_point")
@patch("research.steps.vectorizing.domain.runner.embed_dense_texts")
def test_index_chunks_assigns_sequential_point_ids(
    mock_embed_dense: MagicMock,
    mock_build_point: MagicMock,
    mock_embed_sparse: MagicMock,
) -> None:
    mock_embed_dense.return_value = [[0.1, 0.2]]
    mock_embed_sparse.return_value = [MagicMock()]
    point = MagicMock()
    point.id = 0
    point.payload = {"metadata": {"file_name": "a.pdf", "document_chunk_index": 0}}
    mock_build_point.return_value = point

    qdrant = MagicMock()
    qdrant.collection_exists.return_value = False

    chunk = Chunk(
        content="body",
        metadata=StructureChunkMetadata(file_name="a.pdf", document_chunk_index=0),
    )
    config = {
        "VECTORIZING": {"embedder_model_key": "base_embedder"},
        "EMBEDDINGS": {"base_embedder": {}},
    }

    count = index_chunks([chunk], config, "test-collection", qdrant=qdrant)
    assert count == 1

    mock_build_point.assert_called_once()
    assert mock_build_point.call_args.kwargs["point_id"] == 0

    qdrant.delete_collection.assert_not_called()
    qdrant.create_collection.assert_called_once()
    upload_kwargs = qdrant.upload_points.call_args.kwargs
    assert upload_kwargs["collection_name"] == "test-collection"
    assert upload_kwargs["points"][0].id == 0
    assert upload_kwargs["points"][0].payload["metadata"]["file_name"] == "a.pdf"
    assert "eos_id" not in upload_kwargs["points"][0].payload["metadata"]


@patch("research.steps.vectorizing.domain.runner.embed_sparse_documents", return_value=[MagicMock()])
@patch("research.steps.vectorizing.domain.runner.embed_dense_texts", return_value=[[0.1]])
def test_index_chunks_recreates_existing_collection(
    mock_embed_dense: MagicMock,
    mock_embed_sparse: MagicMock,
) -> None:
    qdrant = MagicMock()
    qdrant.collection_exists.return_value = True

    chunk = Chunk(
        content="x",
        metadata=StructureChunkMetadata(document_chunk_index=0),
    )
    config = {
        "VECTORIZING": {"embedder_model_key": "base_embedder"},
        "EMBEDDINGS": {"base_embedder": {}},
    }
    index_chunks([chunk], config, "col", qdrant=qdrant)

    qdrant.delete_collection.assert_called_once_with("col")
    qdrant.create_collection.assert_called_once()


def test_index_chunks_empty_returns_zero() -> None:
    config = {
        "VECTORIZING": {"embedder_model_key": "base_embedder"},
        "EMBEDDINGS": {"base_embedder": {}},
    }
    assert index_chunks([], config, "col", qdrant=MagicMock()) == 0
