from __future__ import annotations

from pydantic import BaseModel

from research.steps.merge.domain.models import MergedChunk
from research.steps.reranking.domain.models import RerankAttribute


class GroupedChunks(BaseModel):
    attribute_ids: list[str]
    grouped_chunks: list[MergedChunk]


class GroupedContextResult(BaseModel):
    groups: list[GroupedChunks]
    rerank_result: list[RerankAttribute]
