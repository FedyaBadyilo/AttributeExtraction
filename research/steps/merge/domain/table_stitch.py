"""Seam-aware stitching of adjacent table HTML splits."""

from __future__ import annotations

import re
from typing import NamedTuple

from research.steps.chunking.domain.models import TableSeam

TABLE_GAP_MARKER = "<!-- ... -->"

_TR_PATTERN = re.compile(r"<tr\b[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
_CELL_FULL_PATTERN = re.compile(
    r"(<t[dh]\b[^>]*>)(.*?)(</t[dh]>)",
    re.IGNORECASE | re.DOTALL,
)


class IndexedSplit(NamedTuple):
    """One table split loaded from Qdrant for merge stitching."""

    table_chunk_index: int
    point_id: int
    content: str
    seam_to_next: TableSeam | None = None


def _strip_table_header(content: str) -> str:
    """Return table HTML without the repeated header ``<tr>``."""
    match = _TR_PATTERN.search(content)
    if match is None:
        return content
    return content[: match.start()] + content[match.end() :]


def _parse_table_rows(content: str) -> list[str]:
    return _TR_PATTERN.findall(content)


def _replace_cell_inner(row_html: str, cell_col: int, new_inner: str) -> str:
    matches = list(_CELL_FULL_PATTERN.finditer(row_html))
    if cell_col < 0 or cell_col >= len(matches):
        raise ValueError(f"cell_col={cell_col} out of range for row with {len(matches)} cells")
    match = matches[cell_col]
    return row_html[: match.start(2)] + new_inner + row_html[match.end(2) :]


def _cell_inner(row_html: str, cell_col: int) -> str:
    matches = list(_CELL_FULL_PATTERN.finditer(row_html))
    if cell_col < 0 or cell_col >= len(matches):
        raise ValueError(f"cell_col={cell_col} out of range for row with {len(matches)} cells")
    return matches[cell_col].group(2)


def _concat_row_cells(left_row: str, right_row: str) -> str:
    """Horizontally join two data rows by concatenating their cell streams."""
    left_cells = [m.group(0) for m in _CELL_FULL_PATTERN.finditer(left_row)]
    right_cells = [m.group(0) for m in _CELL_FULL_PATTERN.finditer(right_row)]
    return "<tr>" + "".join(left_cells + right_cells) + "</tr>"


def _wrap_table(header_row: str, data_rows: list[str]) -> str:
    return "<table>" + header_row + "".join(data_rows) + "</table>"


def _stitch_adjacent_cluster(cluster: list[IndexedSplit]) -> str:
    """Stitch one adjacency cluster into a single ``<table>`` using seams."""
    first = cluster[0]
    rows = _parse_table_rows(first.content)
    if not rows:
        return first.content
    header_row = rows[0]
    data_rows = list(rows[1:])

    for i in range(len(cluster) - 1):
        seam = cluster[i].seam_to_next
        nxt = cluster[i + 1]
        next_rows = _parse_table_rows(nxt.content)
        next_data = next_rows[1:] if len(next_rows) > 1 else next_rows

        if seam is not None and seam.kind == "cell":
            if not data_rows or not next_data:
                raise ValueError("cell seam requires a data row on both sides")
            cell_col = seam.cell_col
            assert cell_col is not None
            merged_inner = _cell_inner(data_rows[-1], cell_col) + _cell_inner(next_data[0], cell_col)
            data_rows[-1] = _replace_cell_inner(data_rows[-1], cell_col, merged_inner)
            data_rows.extend(next_data[1:])
        elif seam is not None and seam.kind == "cols":
            if not data_rows or not next_data:
                raise ValueError("cols seam requires a data row on both sides")
            data_rows[-1] = _concat_row_cells(data_rows[-1], next_data[0])
            data_rows.extend(next_data[1:])
        else:
            data_rows.extend(next_data)

    return _wrap_table(header_row, data_rows)


def _join_splits_with_header_dedup(indexed_splits: list[IndexedSplit]) -> tuple[str, list[int]]:
    """Join table splits with seam-aware stitch and gap markers between non-adjacent clusters."""
    if not indexed_splits:
        return "", []

    clusters: list[list[IndexedSplit]] = [[indexed_splits[0]]]
    for split in indexed_splits[1:]:
        prev_idx = clusters[-1][-1].table_chunk_index
        if split.table_chunk_index == prev_idx + 1:
            clusters[-1].append(split)
        else:
            clusters.append([split])

    parts: list[str] = []
    point_ids: list[int] = []
    for cluster_i, cluster in enumerate(clusters):
        if cluster_i > 0:
            parts.append(TABLE_GAP_MARKER)
        parts.append(_stitch_adjacent_cluster(cluster))
        point_ids.extend(split.point_id for split in cluster)

    return "\n".join(parts), point_ids
