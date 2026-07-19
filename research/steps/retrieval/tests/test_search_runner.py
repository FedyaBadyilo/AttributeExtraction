from unittest.mock import MagicMock, patch

from research.steps.attribute_grouping.domain.models import AttrType, ClassAttribute
from research.steps.chunking.domain.models import StructureChunkMetadata
from research.steps.retrieval.domain.search.runner import search_attributes

_RETRIEVAL_CONFIG = {
    "RETRIEVAL": {
        "embedder_model_key": "base_embedder",
        "embed_batch_size": 64,
        "prefetch_limit_dense": 20,
        "prefetch_limit_bm25": 20,
        "limit": 10,
    },
    "EMBEDDINGS": {"base_embedder": {}},
}


def _attr(attr_id: str, name: str) -> ClassAttribute:
    return ClassAttribute(
        attr_id=attr_id,
        attr_name=name,
        attr_type=AttrType.STRING,
        for_extraction=True,
    )


def _point(point_id: int, score: float) -> MagicMock:
    point = MagicMock()
    point.id = point_id
    point.score = score
    point.payload = {
        "content": f"chunk-{point_id}",
        "metadata": StructureChunkMetadata(document_chunk_index=point_id).model_dump(mode="json"),
    }
    return point


@patch(
    "research.steps.retrieval.domain.search.runner._embed_hybrid_queries_parallel",
    return_value=([[0.1, 0.2], [0.1, 0.2]], [MagicMock(), MagicMock()]),
)
def test_search_attributes_batches_qdrant_requests(
    mock_embed_hybrid: MagicMock,
) -> None:
    qdrant = MagicMock()
    qdrant.query_batch_points.return_value = [
        MagicMock(points=[_point(1, 0.9)]),
        MagicMock(points=[_point(2, 0.8)]),
    ]

    attrs = {
        "attr_a": _attr("attr_a", "Масса"),
        "attr_b": _attr("attr_b", "Маркировка"),
    }
    results = search_attributes(attrs, "test-collection", _RETRIEVAL_CONFIG, qdrant=qdrant)

    mock_embed_hybrid.assert_called_once()
    embed_texts = mock_embed_hybrid.call_args.args[0]
    assert embed_texts == ["Масса", "Маркировка"]

    qdrant.query_batch_points.assert_called_once()
    batch_kwargs = qdrant.query_batch_points.call_args.kwargs
    assert batch_kwargs["collection_name"] == "test-collection"
    assert len(batch_kwargs["requests"]) == 2

    assert [result.attribute_id for result in results] == ["attr_a", "attr_b"]
    assert results[0].chunks[0].id == 1
    assert results[1].chunks[0].id == 2


@patch(
    "research.steps.retrieval.domain.search.runner._embed_hybrid_queries_parallel",
    return_value=([], []),
)
def test_search_attributes_skips_qdrant_when_no_searchable_attrs(
    mock_embed_hybrid: MagicMock,
) -> None:
    qdrant = MagicMock()
    attrs = {
        "empty": ClassAttribute.model_construct(
            attr_id="empty",
            attr_name="   ",
            attr_type=AttrType.STRING,
            for_extraction=True,
        ),
    }

    results = search_attributes(attrs, "test-collection", _RETRIEVAL_CONFIG, qdrant=qdrant)

    mock_embed_hybrid.assert_not_called()
    qdrant.query_batch_points.assert_not_called()
    assert results == [results[0]]
    assert results[0].attribute_id == "empty"
    assert results[0].chunks == []
