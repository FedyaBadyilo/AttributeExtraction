from research.steps.chunking.domain.models import Chunk, StructureChunkMetadata
from research.steps.vectorizing.domain.points import point_payload


def test_point_payload_stores_document_chunk_index_in_metadata() -> None:
    chunk = Chunk(
        content="**Текст** раздела",
        metadata=StructureChunkMetadata(
            document_chunk_index=3,
            file_name="example.pdf",
            header_path=["Раздел 1"],
            page_numbers=[1],
        ),
    )
    payload = point_payload(chunk)
    meta = payload["metadata"]
    assert meta["document_chunk_index"] == 3
    assert meta["file_name"] == "example.pdf"
    assert "document_chunk_index" not in payload
    assert "eos_id" not in meta
    assert "file_priority" not in meta
    assert "pdf_filename" not in meta
    assert payload["content"] == "**Текст** раздела"
    assert meta["chunk_type"] == "structure"
    assert meta["header_path"] == ["Раздел 1"]
