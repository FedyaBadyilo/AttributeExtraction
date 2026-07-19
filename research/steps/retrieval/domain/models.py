"""Data models for retrieval step search results."""

from pydantic import BaseModel, Field

from research.steps.chunking.domain.models import ChunkMetadata


class ChunkPayload(BaseModel):
    """Payload stored in Qdrant per point: content + chunk metadata."""

    content: str = Field(default="", description="Chunk text")
    metadata: ChunkMetadata = Field(description="Chunk metadata from chunking")


class ChunkHit(BaseModel):
    """One search hit: Qdrant point id, score, and typed payload."""

    id: int = Field(description="Qdrant point id (global ordinal within eos_id collection)")
    score: float = Field(description="Search score")
    payload: ChunkPayload = Field(description="Point payload")


class AttributeSearchResult(BaseModel):
    """One attribute after hybrid search, before merge."""

    attribute_id: str = Field(description="Attribute id")
    chunks: list[ChunkHit] = Field(default_factory=list, description="Top chunks from search")
