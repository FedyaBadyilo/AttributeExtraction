"""HTML table splitting: rowspan-safe rows, mid-span, mid-cell, mid-cols, seams."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from research.steps.chunking.domain.models import TableSeam
from research.steps.chunking.domain.splitters.structure import STRUCTURE_SEPARATORS
from research.steps.chunking.domain.splitters.table_html import (
    _SYNTHETIC_HEADER,
    _cell_htmls,
    _close_rowspans,
    _iter_cells,
    _parse_table_rows,
    _replace_cell_inner,
    _row_from_cells,
    _wrap_table_chunk,
)


@dataclass(frozen=True)
class TableSplitPart:
    """One table HTML fragment and how it joins to the next fragment."""

    content: str
    seam_to_next: TableSeam | None = None


def _raise_split_failed(
    *,
    table_uid: str,
    row_index: int,
    max_tokens: int,
    reason: str,
) -> None:
    uid_part = f"table_uid={table_uid!r}, " if table_uid else ""
    raise ValueError(
        f"table HTML split failed ({reason}; {uid_part}row_index={row_index}, max_tokens={max_tokens})"
    )


def _split_row_mid_cell(
    header_row: str,
    row_html: str,
    max_tokens: int,
    length_function: Callable[[str], int],
    *,
    table_uid: str,
    row_index: int,
    allow_cols: bool = True,
) -> list[TableSplitPart]:
    """Split one oversized data row by cutting the longest cell's inner text.

    When the row wrapper still exceeds the budget after emptying the longest cell,
    fall through to mid-cols (unless ``allow_cols`` is False — atomic one-cell fail).
    """
    cells = list(_iter_cells(row_html))
    if not cells:
        _raise_split_failed(
            table_uid=table_uid,
            row_index=row_index,
            max_tokens=max_tokens,
            reason="oversized row has no cells",
        )
        raise AssertionError("unreachable")

    cell_col = max(range(len(cells)), key=lambda i: length_function(cells[i].group(2)))
    empty_row = _replace_cell_inner(row_html, cell_col, "")
    empty_wrap = length_function(_wrap_table_chunk(header_row, [empty_row]))
    inner = cells[cell_col].group(2)
    # Empty longest cell at/over budget leaves no room for content → mid-cols.
    # (`== max_tokens` used to skip mid-cols and then fail on the first char.)
    if empty_wrap > max_tokens or (inner and empty_wrap >= max_tokens):
        if allow_cols:
            return _split_row_mid_cols(
                header_row,
                row_html,
                max_tokens,
                length_function,
                table_uid=table_uid,
                row_index=row_index,
            )
        _raise_split_failed(
            table_uid=table_uid,
            row_index=row_index,
            max_tokens=max_tokens,
            reason="header+row wrapper exceeds max_chunk_tokens",
        )

    def wrap_len(frag: str) -> int:
        return length_function(
            _wrap_table_chunk(header_row, [_replace_cell_inner(row_html, cell_col, frag)])
        )

    # Wrap-aware exact slices of ``inner`` (lossless when concatenated).
    fragments: list[str] = []
    start = 0
    n = len(inner)
    while start < n:
        lo, hi = start + 1, n
        best: int | None = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if wrap_len(inner[start:mid]) <= max_tokens:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if best is None:
            if allow_cols:
                return _split_row_mid_cols(
                    header_row,
                    row_html,
                    max_tokens,
                    length_function,
                    table_uid=table_uid,
                    row_index=row_index,
                )
            _raise_split_failed(
                table_uid=table_uid,
                row_index=row_index,
                max_tokens=max_tokens,
                reason="mid-cell fragment still exceeds max_chunk_tokens",
            )
            raise AssertionError("unreachable")

        cut = best
        window = inner[start:best]
        for sep in STRUCTURE_SEPARATORS:
            idx = window.rfind(sep)
            if idx == -1:
                continue
            candidate = start + idx + len(sep)
            if candidate > start and wrap_len(inner[start:candidate]) <= max_tokens:
                cut = candidate
                break
        fragments.append(inner[start:cut])
        start = cut

    parts: list[TableSplitPart] = []
    for i, frag in enumerate(fragments):
        content = _wrap_table_chunk(header_row, [_replace_cell_inner(row_html, cell_col, frag)])
        seam = (
            TableSeam(kind="cell", cell_col=cell_col)
            if i < len(fragments) - 1
            else None
        )
        parts.append(TableSplitPart(content=content, seam_to_next=seam))
    return parts


def _split_row_mid_cols(
    header_row: str,
    row_html: str,
    max_tokens: int,
    length_function: Callable[[str], int],
    *,
    table_uid: str,
    row_index: int,
) -> list[TableSplitPart]:
    """Split one oversized row into greedy cell bands; mid-cell inside a single-cell band."""
    cell_htmls = _cell_htmls(row_html)
    if not cell_htmls:
        _raise_split_failed(
            table_uid=table_uid,
            row_index=row_index,
            max_tokens=max_tokens,
            reason="oversized row has no cells",
        )
        raise AssertionError("unreachable")

    parts: list[TableSplitPart] = []
    start = 0
    n = len(cell_htmls)
    while start < n:
        best_end: int | None = None
        for end in range(start + 1, n + 1):
            band_row = _row_from_cells(cell_htmls[start:end])
            if length_function(_wrap_table_chunk(header_row, [band_row])) <= max_tokens:
                best_end = end
            else:
                break

        if best_end is None:
            one_row = _row_from_cells([cell_htmls[start]])
            band_parts = _split_row_mid_cell(
                header_row,
                one_row,
                max_tokens,
                length_function,
                table_uid=table_uid,
                row_index=row_index,
                allow_cols=False,
            )
            next_start = start + 1
            if next_start < n:
                last = band_parts[-1]
                band_parts[-1] = TableSplitPart(
                    content=last.content,
                    seam_to_next=TableSeam(kind="cols", cell_col=next_start),
                )
            parts.extend(band_parts)
            start = next_start
            continue

        band_row = _row_from_cells(cell_htmls[start:best_end])
        seam = (
            TableSeam(kind="cols", cell_col=best_end)
            if best_end < n
            else None
        )
        parts.append(
            TableSplitPart(
                content=_wrap_table_chunk(header_row, [band_row]),
                seam_to_next=seam,
            )
        )
        start = best_end

    return parts


def _split_oversized_atom(
    header_row: str,
    data_rows: list[str],
    start: int,
    atom_end: int,
    max_tokens: int,
    length_function: Callable[[str], int],
    *,
    table_uid: str,
) -> list[TableSplitPart]:
    """Partition an oversized rowspan atom via mid-span, then mid-cell/mid-cols per row."""
    out: list[TableSplitPart] = []
    i = start
    while i <= atom_end:
        one_row = _wrap_table_chunk(header_row, [data_rows[i]])
        if length_function(one_row) > max_tokens:
            out.extend(
                _split_row_mid_cell(
                    header_row,
                    data_rows[i],
                    max_tokens,
                    length_function,
                    table_uid=table_uid,
                    row_index=i + 1,
                )
            )
            i += 1
            continue

        best_j = i
        for j in range(i + 1, atom_end + 1):
            candidate = _wrap_table_chunk(header_row, data_rows[i : j + 1])
            if length_function(candidate) <= max_tokens:
                best_j = j
            else:
                break
        out.append(
            TableSplitPart(
                content=_wrap_table_chunk(header_row, data_rows[i : best_j + 1]),
                seam_to_next=None,
            )
        )
        i = best_j + 1

    for k in range(len(out) - 1):
        if out[k].seam_to_next is None:
            out[k] = TableSplitPart(content=out[k].content, seam_to_next=TableSeam(kind="span"))
    return out


def _fill_missing_row_seams(parts: list[TableSplitPart]) -> list[TableSplitPart]:
    if not parts:
        return parts
    filled: list[TableSplitPart] = []
    for i, part in enumerate(parts):
        if i == len(parts) - 1:
            filled.append(TableSplitPart(content=part.content, seam_to_next=None))
        elif part.seam_to_next is None:
            filled.append(TableSplitPart(content=part.content, seam_to_next=TableSeam(kind="row")))
        else:
            filled.append(part)
    return filled


def _row_empty_longest_wrap_tokens(
    header_row: str,
    row_html: str,
    length_function: Callable[[str], int],
) -> int:
    cells = list(_iter_cells(row_html))
    if not cells:
        return length_function(_wrap_table_chunk(header_row, [row_html]))
    cell_col = max(range(len(cells)), key=lambda i: length_function(cells[i].group(2)))
    empty_row = _replace_cell_inner(row_html, cell_col, "")
    return length_function(_wrap_table_chunk(header_row, [empty_row]))


def _should_demote_header(
    header_row: str,
    data_rows: list[str],
    max_tokens: int,
    length_function: Callable[[str], int],
) -> bool:
    """True when the repeated header leaves no mid-cell budget for an oversized row."""
    if length_function(_wrap_table_chunk(header_row, [])) > max_tokens:
        return True
    for row_html in data_rows:
        full = length_function(_wrap_table_chunk(header_row, [row_html]))
        if full <= max_tokens:
            continue
        if _row_empty_longest_wrap_tokens(header_row, row_html, length_function) > max_tokens:
            return True
    return False


def split_table_html(
    html: str,
    max_tokens: int,
    length_function: Callable[[str], int],
    *,
    table_uid: str = "",
) -> list[TableSplitPart]:
    """Split HTML table by data rows; header ``<tr>`` is repeated in each part.

    Prefer rowspan-safe row cuts. If a minimal closed atom exceeds ``max_tokens``,
    partition it mid-span, then mid-cell (and mid-cols when the row skeleton is too
    wide) on any single row that still exceeds the budget. Seams describe how
    adjacent parts join.

    When the first row is too large to use as a repeated header (no mid-cell budget
    left for data), demote all rows to data under a synthetic empty header.
    """
    if length_function(html) <= max_tokens:
        return [TableSplitPart(content=html, seam_to_next=None)]

    rows = _parse_table_rows(html)
    if not rows:
        _raise_split_failed(
            table_uid=table_uid,
            row_index=0,
            max_tokens=max_tokens,
            reason="no table rows",
        )
        raise AssertionError("unreachable")

    if len(rows) == 1:
        return _fill_missing_row_seams(
            _split_row_mid_cell(
                "",
                rows[0],
                max_tokens,
                length_function,
                table_uid=table_uid,
                row_index=0,
            )
        )

    header_row = rows[0]
    data_rows = rows[1:]
    if _should_demote_header(header_row, data_rows, max_tokens, length_function):
        header_row = _SYNTHETIC_HEADER
        data_rows = rows

    n_data = len(data_rows)

    parts: list[TableSplitPart] = []
    start = 0
    while start < n_data:
        best_end: int | None = None
        cursor = start
        while cursor < n_data:
            closed_end = _close_rowspans(data_rows, start, cursor)
            part_text = _wrap_table_chunk(header_row, data_rows[start : closed_end + 1])
            if length_function(part_text) <= max_tokens:
                best_end = closed_end
                cursor = closed_end + 1
            else:
                break

        if best_end is not None:
            parts.append(
                TableSplitPart(
                    content=_wrap_table_chunk(header_row, data_rows[start : best_end + 1]),
                    seam_to_next=None,
                )
            )
            start = best_end + 1
            continue

        atom_end = _close_rowspans(data_rows, start, start)
        parts.extend(
            _split_oversized_atom(
                header_row,
                data_rows,
                start,
                atom_end,
                max_tokens,
                length_function,
                table_uid=table_uid,
            )
        )
        start = atom_end + 1

    return _fill_missing_row_seams(parts)
