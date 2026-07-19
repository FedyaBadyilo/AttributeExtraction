from __future__ import annotations

from typing import Any

from research.steps.attribute_grouping.domain.models import ClassAttributeSet
from research.steps.merge.domain.models import MergeResult
from research.steps.reranking.domain.models import RerankAttribute
from research.steps.reranking.domain.rerank.runner import rerank_merged_contexts


def run_reranking(
    merge_results: list[MergeResult],
    attr_set: ClassAttributeSet,
    config: dict[str, Any],
    *,
    priority_by_point_id: dict[int, int],
    execution_variant: str | None = None,
) -> list[RerankAttribute]:
    return rerank_merged_contexts(
        merge_results,
        attr_set,
        config,
        priority_by_point_id=priority_by_point_id,
        execution_variant=execution_variant,
    )
