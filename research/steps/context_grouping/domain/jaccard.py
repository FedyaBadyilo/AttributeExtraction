"""Semantic groups from attribute_grouping + Jaccard merge on source point sets."""

from __future__ import annotations

import logging
from typing import Any

from research.steps.attribute_grouping.domain.models import AttributeGroups, ClassAttributeSet

logger = logging.getLogger(__name__)


def _chunk_union(
    group: list[str],
    attr_to_source_point_ids: dict[str, frozenset[int]],
) -> frozenset[int]:
    u: set[int] = set()
    for aid in group:
        u |= set(attr_to_source_point_ids.get(aid, frozenset()))
    return frozenset(u)


def _jaccard(a: frozenset[int], b: frozenset[int]) -> float:
    if not a and not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def merge_groups_by_source_point_jaccard(
    plan_groups: list[list[str]],
    attr_to_source_point_ids: dict[str, frozenset[int]],
    *,
    merge_chunk_jaccard_min: float,
    max_group_size: int,
) -> list[list[str]]:
    """Greedily merge pairs of groups by Jaccard on source point id sets."""
    if not plan_groups:
        return []
    if max_group_size <= 1:
        return [list(g) for g in plan_groups]

    groups = [sorted(g) for g in plan_groups]

    def eligible_for_merge(group: list[str]) -> bool:
        return 1 <= len(group) <= max_group_size - 1

    while True:
        best: tuple[float, int, int] | None = None
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if len(groups[i]) + len(groups[j]) > max_group_size:
                    continue
                if not eligible_for_merge(groups[i]) or not eligible_for_merge(groups[j]):
                    continue
                jac = _jaccard(
                    _chunk_union(groups[i], attr_to_source_point_ids),
                    _chunk_union(groups[j], attr_to_source_point_ids),
                )
                if jac <= merge_chunk_jaccard_min:
                    continue
                if best is None:
                    best = (jac, i, j)
                elif jac > best[0] or (jac == best[0] and (i, j) < (best[1], best[2])):
                    best = (jac, i, j)
        if best is None:
            break
        _, i, j = best
        merged = sorted(groups[i] + groups[j])
        if j > i:
            del groups[j]
            del groups[i]
        else:
            del groups[i]
            del groups[j]
        groups.append(merged)
    return groups


def compute_attribute_groups(
    attr_to_source_point_ids: dict[str, frozenset[int]],
    attributes_set: ClassAttributeSet,
    config: dict[str, Any],
    attr_groups: AttributeGroups,
) -> list[list[str]]:
    """Restrict semantic plan to present attributes, then Jaccard-merge groups."""
    _ = attributes_set
    if not attr_to_source_point_ids:
        return []

    grouping_cfg = config["RERANKING"]["grouping"]
    merge_chunk_jaccard_min = float(grouping_cfg["merge_chunk_jaccard_min"])
    max_group_size = int(grouping_cfg["max_group_size"])

    search_ids = set(attr_to_source_point_ids.keys())
    raw_groups = [[a for a in g.attr_ids if a in search_ids] for g in attr_groups.groups]
    raw_groups = [g for g in raw_groups if g]

    merged = merge_groups_by_source_point_jaccard(
        raw_groups,
        attr_to_source_point_ids,
        merge_chunk_jaccard_min=merge_chunk_jaccard_min,
        max_group_size=max_group_size,
    )

    logger.info(
        "compute_attribute_groups: plan groups=%d -> after merge=%d (merge_chunk_jaccard_min=%s)",
        len(raw_groups),
        len(merged),
        merge_chunk_jaccard_min,
    )
    return merged
