"""Output models for chunking step.

Serialization to JSON via ``model_dump(mode="json")``.
Each chunk is either structure (merged header/list/body text) or table (one table markdown).
"""

from typing import Annotated, ClassVar, Literal, Union

from pydantic import BaseModel, Field, model_validator

ROOT_HEADER_LABEL = "Титульный лист"


class TableSeam(BaseModel):
    """How this table split joins to the next ``table_chunk_index`` when adjacent."""

    kind: Literal["row", "span", "cell", "cols"] = Field(
        description=(
            "Join recipe: concat data rows (row/span), merge one cell's text (cell), "
            "or concat cell streams in one row (cols)"
        ),
    )
    cell_col: int | None = Field(
        default=None,
        description=(
            "0-based <td>/<th> index within the data row; required when kind=cell "
            "(which cell to merge) or kind=cols (first cell index of the right band)"
        ),
    )

    @model_validator(mode="after")
    def _cell_col_required_for_cell(self) -> "TableSeam":
        if self.kind in ("cell", "cols") and self.cell_col is None:
            raise ValueError(f"cell_col is required when kind={self.kind!r}")
        if self.kind not in ("cell", "cols") and self.cell_col is not None:
            raise ValueError("cell_col is only allowed when kind is 'cell' or 'cols'")
        return self


class ChunkMetadataBase(BaseModel):
    """Base chunk metadata; discriminated by ``chunk_type``."""

    CHUNK_TYPE_STRUCTURE: ClassVar[str] = "structure"
    CHUNK_TYPE_TABLE: ClassVar[str] = "table"

    chunk_type: Literal["structure", "table"] = Field(description="Chunk type for union discriminator")
    file_name: str = Field(
        default="",
        description="Полное имя файла-источника (pdf_filename из examples_manifest.json)",
    )
    header_path: list[str] = Field(
        default_factory=list,
        description=(
            "Path of header titles (level_1=1 only) from root to current section; "
            f"[{ROOT_HEADER_LABEL}] before first header"
        ),
    )
    document_chunk_index: int = Field(
        description="Zero-based index of the chunk within its source PDF (ChunkedDocument order)",
    )


class StructureChunkMetadata(ChunkMetadataBase):
    """Metadata for a structure chunk: pages and table uids referenced in the chunk."""

    chunk_type: Literal["structure"] = ChunkMetadataBase.CHUNK_TYPE_STRUCTURE
    page_numbers: list[int] | None = Field(
        default=None,
        description="1-based page numbers this chunk spans (sorted unique)",
    )
    table_uids: list[str] = Field(
        default_factory=list,
        description="Table uids referenced in this chunk (order of appearance)",
    )


class TableChunkMetadata(ChunkMetadataBase):
    """Metadata for a table chunk."""

    chunk_type: Literal["table"] = ChunkMetadataBase.CHUNK_TYPE_TABLE
    table_uid: str = Field(description="Table unique identifier")
    table_chunk_index: int = Field(description="Zero-based index of this split within its table")
    seam_to_next: TableSeam | None = Field(
        default=None,
        description="Join recipe to the next split; None on the last split of the table",
    )


ChunkMetadata = Annotated[
    Union[StructureChunkMetadata, TableChunkMetadata],
    Field(discriminator="chunk_type"),
]


class Chunk(BaseModel):
    """One chunk in document order: structure text or a single table markdown."""

    content: str = Field(
        description="Chunk content: merged structure text or table markdown",
    )
    metadata: ChunkMetadata


class ChunkedDocument(BaseModel):
    """Root output of ``chunk_document`` (one artifact per PDF)."""

    eos_id: int = Field(description="Идентификатор карточки изделия")
    pdf_filename: str = Field(description="Имя PDF-файла")
    chunks: list[Chunk] = Field(default_factory=list, description="Chunks in document order")
