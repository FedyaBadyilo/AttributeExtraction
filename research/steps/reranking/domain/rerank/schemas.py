"""Pydantic schemas for LLM rerank structured output (per-request dynamic enum for chunk numbers)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from research.steps.merge.domain.models import MergedChunk

CHUNK_NUMBER_DESCRIPTION = (
    "Chunk number as in <chunk number=\"N\"> in this request only. "
    "Must be one of the values listed in the JSON schema enum for this field."
)


def build_attribute_rerank_response_model(num_chunks: int) -> type[BaseModel]:
    """
    Schema for one rerank call: `chunk_number` enum = 1..num_chunks (same numbering as in the user prompt).
    `scores` length is fixed to num_chunks. Use num_chunks = len(chunks) passed to build_user_prompt.
    """
    if num_chunks < 1:
        raise ValueError("num_chunks must be >= 1")
    chunk_numbers = list(range(1, num_chunks + 1))

    class ChunkRerankScoreRow(BaseModel):
        chunk_number: int = Field(
            description=CHUNK_NUMBER_DESCRIPTION,
            json_schema_extra={"enum": chunk_numbers},
        )
        relevance_score: float = Field(
            ge=0.0,
            le=1.0,
            description="Relevance score in [0, 1] (inclusive).",
        )

    class AttributeRerankResponseDyn(BaseModel):
        scores: list[ChunkRerankScoreRow] = Field(
            description="Exactly one score per chunk from the user message (one entry per chunk number).",
            min_length=num_chunks,
            max_length=num_chunks,
        )

    AttributeRerankResponseDyn.model_rebuild()
    return AttributeRerankResponseDyn


def chunk_numbers_to_source_point_ids(chunks: list[MergedChunk]) -> dict[int, tuple[int, ...]]:
    """Maps prompt chunk index 1..n to source_point_ids (same order as in build_user_prompt)."""
    return {i: c.source_point_ids for i, c in enumerate(chunks, start=1)}
