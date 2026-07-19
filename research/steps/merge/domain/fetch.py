"""Qdrant fetch helpers for structure and table chunks used by context merge."""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from research.steps.chunking.domain.models import ChunkMetadataBase, TableChunkMetadata
from research.steps.merge.domain.table_stitch import IndexedSplit
from research.steps.retrieval.domain.models import ChunkPayload

logger = logging.getLogger(__name__)

SCROLL_PAGE_SIZE = 100


def _point_id(point: Any) -> int:
    if point.id is None:
        raise ValueError("Qdrant point is missing id")
    return int(point.id)


def _indexed_split_from_payload(point: Any) -> IndexedSplit:
    payload = ChunkPayload.model_validate(point.payload)
    table_metadata = TableChunkMetadata.model_validate(payload.metadata.model_dump())
    return IndexedSplit(
        table_chunk_index=table_metadata.table_chunk_index,
        point_id=_point_id(point),
        content=payload.content,
        seam_to_next=table_metadata.seam_to_next,
    )


def _get_table_splits_sorted(
    qdrant: QdrantClient,
    collection_name: str,
    table_uid: str,
) -> list[IndexedSplit]:
    """Return indexed splits for a table, sorted by table_chunk_index."""
    scroll_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="metadata.chunk_type",
                match=qdrant_models.MatchValue(value=ChunkMetadataBase.CHUNK_TYPE_TABLE),
            ),
            qdrant_models.FieldCondition(
                key="metadata.table_uid",
                match=qdrant_models.MatchValue(value=table_uid),
            ),
        ]
    )
    all_points: list[Any] = []
    offset: Any = None
    while True:
        points, next_offset = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=SCROLL_PAGE_SIZE,
            offset=offset,
            with_payload=True,
        )
        all_points.extend(points)
        if next_offset is None:
            break
        offset = next_offset
    if not all_points:
        logger.warning("Table chunk not found for table_uid=%s", table_uid)
        return []
    splits = [_indexed_split_from_payload(p) for p in all_points]
    return sorted(splits, key=lambda s: s.table_chunk_index)


def _fetch_selected_table_chunks(
    qdrant: QdrantClient,
    collection_name: str,
    point_ids: list[int],
) -> list[tuple[str, IndexedSplit]]:
    """Fetch table chunks by point ids. Returns (table_uid, IndexedSplit)."""
    if not point_ids:
        return []
    points = qdrant.retrieve(
        collection_name=collection_name,
        ids=point_ids,
        with_payload=True,
    )
    result: list[tuple[str, IndexedSplit]] = []
    for point in points:
        payload = ChunkPayload.model_validate(point.payload)
        metadata = payload.metadata
        if metadata.chunk_type != ChunkMetadataBase.CHUNK_TYPE_TABLE:
            continue
        table_metadata = TableChunkMetadata.model_validate(metadata.model_dump())
        result.append(
            (
                table_metadata.table_uid,
                IndexedSplit(
                    table_chunk_index=table_metadata.table_chunk_index,
                    point_id=_point_id(point),
                    content=payload.content,
                    seam_to_next=table_metadata.seam_to_next,
                ),
            )
        )
    return result


def _get_structure_chunk(
    qdrant: QdrantClient,
    collection_name: str,
    section_id: int,
) -> tuple[str, list[str], list[str]]:
    """Fetch structure chunk by section_id (structure point id)."""
    points = qdrant.retrieve(
        collection_name=collection_name,
        ids=[section_id],
        with_payload=True,
    )
    if not points:
        logger.warning("Structure chunk not found for section_id=%s", section_id)
        return ("", [], [])
    payload = ChunkPayload.model_validate(points[0].payload)
    metadata = payload.metadata
    return (
        payload.content,
        list(metadata.table_uids),
        list(metadata.header_path),
    )


def _get_structure_by_table_uid(
    qdrant: QdrantClient,
    collection_name: str,
    table_uid: str,
) -> tuple[int, str, list[str], list[str]]:
    """Find the single structure chunk that owns table_uid."""
    scroll_filter = qdrant_models.Filter(
        must=[
            qdrant_models.FieldCondition(
                key="metadata.chunk_type",
                match=qdrant_models.MatchValue(value=ChunkMetadataBase.CHUNK_TYPE_STRUCTURE),
            ),
            qdrant_models.FieldCondition(
                key="metadata.table_uids",
                match=qdrant_models.MatchAny(any=[table_uid]),
            ),
        ]
    )
    all_points: list[Any] = []
    offset: Any = None
    while True:
        points, next_offset = qdrant.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=SCROLL_PAGE_SIZE,
            offset=offset,
            with_payload=True,
        )
        all_points.extend(points)
        if next_offset is None:
            break
        offset = next_offset
    if len(all_points) != 1:
        raise ValueError(
            f"Expected exactly 1 structure chunk for table_uid={table_uid}, found {len(all_points)}"
        )
    point = all_points[0]
    structure_point_id = _point_id(point)
    typed_payload = ChunkPayload.model_validate(point.payload)
    return (
        structure_point_id,
        typed_payload.content,
        list(typed_payload.metadata.table_uids),
        list(typed_payload.metadata.header_path),
    )
