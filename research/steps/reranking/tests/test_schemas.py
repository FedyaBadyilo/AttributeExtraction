from __future__ import annotations

from research.steps.reranking.domain.rerank.schemas import (
    build_attribute_rerank_response_model,
    chunk_numbers_to_source_point_ids,
)
from research.steps.merge.domain.models import MergedChunk


def _merged_chunk(label: str, *, point_id: int = 1) -> MergedChunk:
    return MergedChunk(
        source_point_ids=[point_id],
        display_point_id=point_id,
        content=f"content-{label}",
        header_path=["H1"],
        section_id=point_id,
    )


def test_build_attribute_rerank_response_model_enum_and_length() -> None:
    model = build_attribute_rerank_response_model(3)
    schema = model.model_json_schema()
    chunk_number_schema = schema["$defs"]["ChunkRerankScoreRow"]["properties"]["chunk_number"]
    assert chunk_number_schema["enum"] == [1, 2, 3]

    scores_field = schema["properties"]["scores"]
    assert scores_field["minItems"] == 3
    assert scores_field["maxItems"] == 3

    instance = model.model_validate(
        {
            "scores": [
                {"chunk_number": 1, "relevance_score": 0.9},
                {"chunk_number": 2, "relevance_score": 0.5},
                {"chunk_number": 3, "relevance_score": 0.1},
            ]
        }
    )
    assert len(instance.scores) == 3


def test_chunk_numbers_to_source_point_ids_one_based_order() -> None:
    chunks = [
        _merged_chunk("a", point_id=1),
        _merged_chunk("b", point_id=2),
        _merged_chunk("c", point_id=3),
    ]
    mapping = chunk_numbers_to_source_point_ids(chunks)
    assert mapping == {1: (1,), 2: (2,), 3: (3,)}
