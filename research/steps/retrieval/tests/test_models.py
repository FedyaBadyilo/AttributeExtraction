from research.steps.chunking.domain.models import StructureChunkMetadata
from research.steps.retrieval.domain.models import AttributeSearchResult, ChunkHit, ChunkPayload


def test_attribute_search_result_contract_is_search_only() -> None:
    result = AttributeSearchResult(
        attribute_id="attr-1",
        chunks=[
            ChunkHit(
                id=1,
                score=0.75,
                payload=ChunkPayload(
                    content="section text",
                    metadata=StructureChunkMetadata(document_chunk_index=0),
                ),
            )
        ],
    )

    payload = result.model_dump(mode="json")

    assert payload["attribute_id"] == "attr-1"
    assert payload["chunks"][0]["id"] == 1
    assert "merged_chunks" not in payload
