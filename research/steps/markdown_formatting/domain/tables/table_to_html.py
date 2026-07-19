"""Convert dedoc ``Table.cells`` to HTML with native rowspan/colspan."""

from __future__ import annotations

import html

from dedoc.api.schema.table import Table


def _normalize_cell_text(text: str) -> str:
    return " ".join(text.split())


def _escape_cell_text(text: str) -> str:
    """Escape ``&``, ``<``, ``>`` in cell text (quotes stay literal inside elements)."""
    return html.escape(text, quote=False)


def dedoc_table_to_html(table: Table) -> str:
    """
    Convert a dedoc API ``Table`` to HTML.

    Invisible cells are skipped. Visible cells keep native ``rowspan`` /
    ``colspan``. Cell text is HTML-escaped. No index column and no flatten /
    comment markers for merged spans.
    """
    row_parts: list[str] = []
    for row in table.cells:
        cell_parts: list[str] = []
        for cell in row:
            if cell.invisible:
                continue
            if cell.rowspan < 1 or cell.colspan < 1:
                raise ValueError(
                    f"invalid cell span for table {table.metadata.uid!r}: "
                    f"rowspan={cell.rowspan}, colspan={cell.colspan}"
                )
            text = _normalize_cell_text("\n".join(line.text for line in cell.lines))
            attrs: list[str] = []
            if cell.rowspan != 1:
                attrs.append(f'rowspan="{cell.rowspan}"')
            if cell.colspan != 1:
                attrs.append(f'colspan="{cell.colspan}"')
            attr_str = (" " + " ".join(attrs)) if attrs else ""
            cell_parts.append(f"<td{attr_str}>{_escape_cell_text(text)}</td>")
        row_parts.append("<tr>" + "".join(cell_parts) + "</tr>")

    if not row_parts:
        return ""
    return "<table>" + "".join(row_parts) + "</table>"
