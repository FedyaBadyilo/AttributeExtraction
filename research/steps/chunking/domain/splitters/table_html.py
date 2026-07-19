"""Low-level HTML table row/cell helpers used by table splitting."""

from __future__ import annotations

import re
from collections.abc import Iterator
from re import Match

_TR_PATTERN = re.compile(r"<tr\b[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
_CELL_OPEN_PATTERN = re.compile(r"<t[dh]\b([^>]*)>", re.IGNORECASE)
_CELL_FULL_PATTERN = re.compile(
    r"(<t[dh]\b[^>]*>)(.*?)(</t[dh]>)",
    re.IGNORECASE | re.DOTALL,
)
_ROWSPAN_ATTR_PATTERN = re.compile(r"""\browspan\s*=\s*(?:["'](\d+)["']|(\d+))""", re.IGNORECASE)

_SYNTHETIC_HEADER = "<tr></tr>"


def _parse_table_rows(html: str) -> list[str]:
    return _TR_PATTERN.findall(html)


def _row_rowspans(row_html: str) -> list[int]:
    spans: list[int] = []
    for attrs in _CELL_OPEN_PATTERN.findall(row_html):
        match = _ROWSPAN_ATTR_PATTERN.search(attrs)
        if match:
            spans.append(int(match.group(1) or match.group(2)))
        else:
            spans.append(1)
    return spans


def _close_rowspans(rows: list[str], start: int, end: int) -> int:
    """Extend ``end`` until every rowspan starting in ``[start, end]`` is closed."""
    n = len(rows)
    while True:
        required = end
        for i in range(start, end + 1):
            for rowspan in _row_rowspans(rows[i]):
                if rowspan < 1:
                    raise ValueError(f"invalid rowspan={rowspan} in table row {i}")
                required = max(required, i + rowspan - 1)
        if required >= n:
            raise ValueError(
                f"rowspan extends past last table row (row_index={start}, required_end={required}, n_rows={n})"
            )
        if required == end:
            return end
        end = required


def _wrap_table_chunk(header_row: str, data_rows: list[str]) -> str:
    return "<table>" + header_row + "".join(data_rows) + "</table>"


def _iter_cells(row_html: str) -> Iterator[Match[str]]:
    """Match objects for each ``<td>/<th>`` in ``row_html`` (groups: open, inner, close)."""
    return _CELL_FULL_PATTERN.finditer(row_html)


def _replace_cell_inner(row_html: str, cell_col: int, new_inner: str) -> str:
    matches = list(_iter_cells(row_html))
    if cell_col < 0 or cell_col >= len(matches):
        raise ValueError(f"cell_col={cell_col} out of range for row with {len(matches)} cells")
    match = matches[cell_col]
    return row_html[: match.start(2)] + new_inner + row_html[match.end(2) :]


def _cell_htmls(row_html: str) -> list[str]:
    """Full ``<td>…</td>`` / ``<th>…</th>`` strings in document order."""
    return [match.group(0) for match in _iter_cells(row_html)]


def _row_from_cells(cell_htmls: list[str]) -> str:
    return "<tr>" + "".join(cell_htmls) + "</tr>"


def _concat_row_cells(left_row: str, right_row: str) -> str:
    """Horizontally join two data rows by concatenating their cell streams."""
    return _row_from_cells(_cell_htmls(left_row) + _cell_htmls(right_row))
