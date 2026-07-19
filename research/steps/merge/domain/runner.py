"""Build merged context blocks from hybrid retrieval hits."""

from __future__ import annotations

from typing import Any

from infra.qdrant import get_qdrant_client
from qdrant_client import QdrantClient

from research.steps.common.downstream_text import remove_placeholder_blocks
from research.steps.merge.domain.context_merge import get_merged_chunks_for_attribute
from research.steps.merge.domain.models import MergedChunk, MergeResult
from research.steps.retrieval.domain.models import AttributeSearchResult


def run_merge(
    search_rows: list[AttributeSearchResult],
    collection_name: str,
    config: dict[str, Any],
    *,
    qdrant: QdrantClient | None = None,
) -> list[MergeResult]:
    """Return one merge result per search row (same order)."""
    qdrant = qdrant or get_qdrant_client(config)
    merge_cfg = config["MERGE"]
    expansion_char_budget_structure = int(merge_cfg["expansion_char_budget_structure"])
    expansion_char_budget_table = int(merge_cfg["expansion_char_budget_table"])

    out: list[MergeResult] = []

    for row in search_rows:
        if not row.chunks:
            out.append(MergeResult(attribute_id=row.attribute_id, merged_chunks=[]))
            continue

        rows = get_merged_chunks_for_attribute(
            row.chunks,
            qdrant,
            collection_name,
            expansion_char_budget_structure=expansion_char_budget_structure,
            expansion_char_budget_table=expansion_char_budget_table,
        )
        merged_chunks: list[MergedChunk] = []
        for merged_row in rows:
            merged_chunks.append(
                MergedChunk(
                    source_point_ids=merged_row.source_point_ids,
                    display_point_id=merged_row.display_point_id,
                    content=remove_placeholder_blocks(merged_row.merged_text),
                    header_path=merged_row.header_path,
                    section_id=merged_row.section_id,
                )
            )

        out.append(MergeResult(attribute_id=row.attribute_id, merged_chunks=merged_chunks))

    return out
