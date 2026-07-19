from __future__ import annotations

from pydantic import BaseModel

from research.steps.merge.domain.models import MergedChunk


class RerankChunk(MergedChunk):
    rerank_score: float


class RerankAttribute(BaseModel):
    attribute_id: str
    rerank_chunks: list[RerankChunk]
