import pytest

from research.steps.chunking.domain.build import strip_header_line_to_clean_title
from research.steps.chunking.domain.models import (
    Chunk,
    ChunkedDocument,
    StructureChunkMetadata,
    TableChunkMetadata,
    TableSeam,
)


def test_table_chunk_metadata_has_table_chunk_index_field() -> None:
    fields = TableChunkMetadata.model_fields
    assert "table_chunk_index" in fields
    assert "seam_to_next" in fields
    meta = TableChunkMetadata(table_uid="t1", table_chunk_index=0, document_chunk_index=0)
    assert meta.table_chunk_index == 0
    assert meta.seam_to_next is None


def test_table_seam_requires_cell_col_for_cell_kind() -> None:
    seam = TableSeam(kind="cell", cell_col=2)
    assert seam.cell_col == 2
    with pytest.raises(ValueError, match="cell_col"):
        TableSeam(kind="cell")


def test_table_seam_requires_cell_col_for_cols_kind() -> None:
    seam = TableSeam(kind="cols", cell_col=3)
    assert seam.kind == "cols"
    assert seam.cell_col == 3
    with pytest.raises(ValueError, match="cell_col"):
        TableSeam(kind="cols")
    with pytest.raises(ValueError, match="cell_col"):
        TableSeam(kind="row", cell_col=0)


def test_chunk_accepts_content_field() -> None:
    chunk = Chunk.model_validate(
        {
            "content": "body",
            "metadata": {"chunk_type": "structure", "document_chunk_index": 0},
        }
    )
    assert chunk.content == "body"
    assert chunk.metadata.document_chunk_index == 0


def test_chunked_document_roundtrip() -> None:
    doc = ChunkedDocument(
        eos_id=2203009,
        pdf_filename="example.pdf",
        chunks=[
            Chunk(
                content="section",
                metadata=StructureChunkMetadata(
                    document_chunk_index=0,
                    header_path=["Раздел 1"],
                ),
            ),
            Chunk(
                content="| a | b |\n| --- | --- |\n| 1 | 2 |",
                metadata=TableChunkMetadata(
                    document_chunk_index=1,
                    table_uid="t1",
                    table_chunk_index=0,
                ),
            ),
        ],
    )
    restored = ChunkedDocument.model_validate(doc.model_dump())
    assert restored.eos_id == 2203009
    assert restored.pdf_filename == "example.pdf"
    assert len(restored.chunks) == 2
    assert restored.chunks[1].metadata.chunk_type == "table"


def test_strip_header_line_to_clean_title() -> None:
    line = "# **1. Введение**"
    assert strip_header_line_to_clean_title(line) == "1. Введение"
