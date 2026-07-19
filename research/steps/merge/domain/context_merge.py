"""Merge structure and table chunks by substituting table HTML into placeholders."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel
from qdrant_client import QdrantClient

from research.steps.chunking.domain.models import ChunkMetadataBase
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
)
from research.steps.merge.domain.fetch import (
    _fetch_selected_table_chunks,
    _get_structure_by_table_uid,
    _get_structure_chunk,
    _get_table_splits_sorted,
)
from research.steps.merge.domain.selection import (
    _select_expanded_table_splits,
    _select_optional_table_splits,
)
from research.steps.merge.domain.table_stitch import (
    TABLE_GAP_MARKER,
    IndexedSplit,
    _join_splits_with_header_dedup,
    _strip_table_header,
)
from research.steps.retrieval.domain.models import ChunkHit

__all__ = [
    "TABLE_GAP_MARKER",
    "IndexedSplit",
    "MergedChunkRow",
    "_get_structure_by_table_uid",
    "_join_splits_with_header_dedup",
    "_strip_table_header",
    "build_merged_section",
    "get_merged_chunks_for_attribute",
]


class MergedChunkRow(BaseModel):
    """One merged row from retrieval search hits."""

    display_point_id: int
    merged_text: str
    header_path: list[str]
    source_point_ids: list[int]
    section_id: int


def build_merged_section(
    section_id: int,
    selected_table_point_ids: list[int],
    qdrant: QdrantClient,
    collection_name: str,
    *,
    expansion_char_budget: int | None,
) -> MergedChunkRow:
    """Build one merged section block from structure and table splits."""
    structure_content, table_uids, header_path = _get_structure_chunk(
        qdrant, collection_name, section_id
    )
    selected_rows = _fetch_selected_table_chunks(qdrant, collection_name, selected_table_point_ids)
    selected_by_uid: dict[str, list[IndexedSplit]] = defaultdict(list)
    for table_uid, split in selected_rows:
        selected_by_uid[table_uid].append(split)

    merged = structure_content
    source_ids: list[int] = [section_id]

    for uid in table_uids:
        placeholder = TABLE_PLACEHOLDER_TEMPLATE.format(uid)
        if placeholder not in merged:
            if uid in selected_by_uid:
                raise ValueError(
                    f"Selected table placeholder missing in structure section_id={section_id} "
                    f"for table_uid={uid}"
                )
            continue

        if uid not in selected_by_uid:
            if expansion_char_budget is not None:
                splits_indexed = _get_table_splits_sorted(qdrant, collection_name, uid)
                included_splits = _select_optional_table_splits(
                    splits_indexed,
                    expansion_char_budget=expansion_char_budget,
                    merged=merged,
                    placeholder=placeholder,
                )
                table_content, included_ids = _join_splits_with_header_dedup(included_splits)
                source_ids.extend(included_ids)
                merged = merged.replace(placeholder, table_content)
            else:
                merged = merged.replace(placeholder, "")
            continue

        selected_splits = sorted(selected_by_uid[uid], key=lambda x: x.table_chunk_index)
        if expansion_char_budget is None:
            included_splits = selected_splits
        else:
            all_splits_indexed = _get_table_splits_sorted(qdrant, collection_name, uid)
            included_splits = _select_expanded_table_splits(
                all_splits_indexed,
                selected_splits,
                expansion_char_budget=expansion_char_budget,
                merged=merged,
                placeholder=placeholder,
            )
        table_content, included_ids = _join_splits_with_header_dedup(included_splits)
        merged = merged.replace(placeholder, table_content)
        source_ids.extend(included_ids)

    missing_selected = set(selected_table_point_ids) - set(source_ids)
    if missing_selected:
        raise ValueError(
            f"Selected table point ids not merged for section_id={section_id}: "
            f"{sorted(missing_selected)}"
        )

    return MergedChunkRow(
        display_point_id=section_id,
        merged_text=merged,
        header_path=header_path,
        source_point_ids=sorted(set(source_ids)),
        section_id=section_id,
    )


def get_merged_chunks_for_attribute(
    chunks: list[ChunkHit],
    qdrant: QdrantClient,
    collection_name: str,
    *,
    expansion_char_budget_structure: int,
    expansion_char_budget_table: int,
) -> list[MergedChunkRow]:
    """Build one merged block per section from search hits."""
    sections: dict[int, list[ChunkHit]] = defaultdict(list)
    for chunk in chunks:
        metadata = chunk.payload.metadata
        if metadata.chunk_type == ChunkMetadataBase.CHUNK_TYPE_STRUCTURE:
            section_id = chunk.id
        elif metadata.chunk_type == ChunkMetadataBase.CHUNK_TYPE_TABLE:
            section_id, _, _, _ = _get_structure_by_table_uid(
                qdrant, collection_name, metadata.table_uid
            )
        else:
            continue
        sections[section_id].append(chunk)

    result: list[MergedChunkRow] = []
    for section_id, section_chunks in sections.items():
        has_structure = any(
            c.payload.metadata.chunk_type == ChunkMetadataBase.CHUNK_TYPE_STRUCTURE
            for c in section_chunks
        )
        has_table = any(
            c.payload.metadata.chunk_type == ChunkMetadataBase.CHUNK_TYPE_TABLE
            for c in section_chunks
        )
        expansion_char_budget = (
            expansion_char_budget_table
            if has_table
            else expansion_char_budget_structure
        )
        selected_table_ids = [
            c.id
            for c in section_chunks
            if c.payload.metadata.chunk_type == ChunkMetadataBase.CHUNK_TYPE_TABLE
        ]
        result.append(
            build_merged_section(
                section_id,
                selected_table_ids,
                qdrant,
                collection_name,
                expansion_char_budget=expansion_char_budget,
            )
        )

    return result
