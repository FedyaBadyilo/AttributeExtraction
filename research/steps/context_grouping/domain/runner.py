"""Build context attribute groups from rerank evidence."""

from __future__ import annotations

from typing import Any

from research.steps.attribute_grouping.domain.models import (
    AttributeGroup,
    AttributeGroups,
    ClassAttributeSet,
)
from research.steps.context_grouping.domain.jaccard import compute_attribute_groups
from research.steps.reranking.domain.models import RerankAttribute


def attr_to_source_point_ids(rerank_list: list[RerankAttribute]) -> dict[str, frozenset[int]]:
    """Union source_point_ids across all reranked blocks for each attribute."""
    return {
        ra.attribute_id: frozenset().union(*(set(rc.source_point_ids) for rc in ra.rerank_chunks))
        for ra in rerank_list
    }


def build_context_attribute_groups(
    rerank_by_attribute: list[RerankAttribute],
    attributes_set: ClassAttributeSet,
    config: dict[str, Any],
    attr_groups: AttributeGroups,
) -> AttributeGroups:
    group_lists = compute_attribute_groups(
        attr_to_source_point_ids(rerank_by_attribute),
        attributes_set,
        config,
        attr_groups,
    )
    return AttributeGroups(groups=[AttributeGroup(attr_ids=sorted(attr_ids)) for attr_ids in group_lists])
