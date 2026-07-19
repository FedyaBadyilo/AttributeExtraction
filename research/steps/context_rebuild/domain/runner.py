"""Rebuild final grouped extraction context after context grouping."""

from __future__ import annotations

from collections import defaultdict

from qdrant_client import QdrantClient

from research.steps.attribute_grouping.domain.models import AttributeGroups
from research.steps.common.downstream_text import remove_placeholder_blocks
from research.steps.context_rebuild.domain.models import GroupedChunks, GroupedContextResult
from research.steps.merge.domain.context_merge import build_merged_section
from research.steps.merge.domain.models import MergedChunk, MergeResult
from research.steps.reranking.domain.models import RerankAttribute

ChunkKey = tuple[int, ...]


def _section_by_source_ids(merge_results: list[MergeResult]) -> dict[ChunkKey, int]:
    out: dict[ChunkKey, int] = {}
    for result in merge_results:
        for chunk in result.merged_chunks:
            out[chunk.source_point_ids] = chunk.section_id
    return out


def _rerank_by_attribute(rerank_result: list[RerankAttribute]) -> dict[str, RerankAttribute]:
    return {row.attribute_id: row for row in rerank_result}


def rebuild_grouped_context(
    attr_groups: AttributeGroups,
    rerank_result: list[RerankAttribute],
    merge_results: list[MergeResult],
    qdrant: QdrantClient,
    collection_name: str,
) -> GroupedContextResult:
    """Join grouping + rerank + merge artifacts and rebuild one context chunk per parent section."""
    section_by_source_ids = _section_by_source_ids(merge_results)
    rerank_by_attr = _rerank_by_attribute(rerank_result)
    groups_out: list[GroupedChunks] = []

    for group in attr_groups.groups:
        section_source_ids: dict[int, set[int]] = defaultdict(set)
        section_order: list[int] = []

        for attribute_id in group.attr_ids:
            rerank_attr = rerank_by_attr.get(attribute_id)
            if rerank_attr is None:
                raise ValueError(f"Missing rerank result for grouped attribute {attribute_id!r}")
            for chunk in rerank_attr.rerank_chunks:
                if chunk.source_point_ids not in section_by_source_ids:
                    raise ValueError(
                        "Missing merge chunk for rerank source_point_ids "
                        f"{chunk.source_point_ids} (attribute_id={attribute_id!r})"
                    )
                section_id = section_by_source_ids[chunk.source_point_ids]
                if section_id not in section_source_ids:
                    section_order.append(section_id)
                section_source_ids[section_id].update(chunk.source_point_ids)

        rebuilt_chunks: list[MergedChunk] = []
        for section_id in section_order:
            table_ids = sorted(pid for pid in section_source_ids[section_id] if pid != section_id)
            new_row = build_merged_section(
                section_id,
                table_ids,
                qdrant,
                collection_name,
                expansion_char_budget=None,
            )
            rebuilt_chunks.append(
                MergedChunk(
                    source_point_ids=new_row.source_point_ids,
                    display_point_id=new_row.display_point_id,
                    content=remove_placeholder_blocks(new_row.merged_text),
                    header_path=new_row.header_path,
                    section_id=section_id,
                )
            )

        groups_out.append(
            GroupedChunks(
                attribute_ids=list(group.attr_ids),
                grouped_chunks=rebuilt_chunks,
            )
        )

    return GroupedContextResult(groups=groups_out, rerank_result=rerank_result)
