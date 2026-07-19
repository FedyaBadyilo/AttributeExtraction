"""Tests for table → HTML conversion."""

import pytest
from dedoc.api.schema.cell_with_meta import CellWithMeta
from dedoc.api.schema.line_with_meta import LineWithMeta
from dedoc.api.schema.table import Table
from dedoc.api.schema.table_metadata import TableMetadata

from research.steps.markdown_formatting.domain.tables.table_to_html import (
    dedoc_table_to_html,
)


def _line(text: str) -> LineWithMeta:
    return LineWithMeta(text=text, annotations=[])


def _cell(
    text: str,
    *,
    rowspan: int = 1,
    colspan: int = 1,
    invisible: bool = False,
) -> CellWithMeta:
    return CellWithMeta(
        lines=[_line(text)] if text else [],
        rowspan=rowspan,
        colspan=colspan,
        invisible=invisible,
    )


def _table(rows: list[list[CellWithMeta]], uid: str = "t1") -> Table:
    return Table(
        cells=rows,
        metadata=TableMetadata(page_id=0, uid=uid, rotated_angle=0.0, title=""),
    )


def test_dedoc_table_to_html_escapes_angle_brackets_and_ampersand() -> None:
    table = _table(
        [
            [_cell("name"), _cell("value")],
            [_cell("сила < 10 Н & more"), _cell("ok")],
            [_cell("after"), _cell("still here")],
        ]
    )
    result = dedoc_table_to_html(table)

    assert "сила &lt; 10 Н &amp; more" in result
    assert "ok" in result
    assert "still here" in result
    assert result.startswith("<table>")
    assert result.endswith("</table>")
    assert result.count("<tr>") == 3


def test_dedoc_table_to_html_skips_invisible_cells_and_keeps_spans() -> None:
    table = _table(
        [
            [_cell("A", colspan=2), _cell("dup", invisible=True)],
            [_cell("b"), _cell("c")],
        ]
    )
    result = dedoc_table_to_html(table)

    assert 'colspan="2"' in result
    assert "dup" not in result
    assert "<td>A</td>" not in result  # A has colspan
    assert '<td colspan="2">A</td>' in result
    assert "<td>b</td><td>c</td>" in result


def test_dedoc_table_to_html_emits_rowspan() -> None:
    table = _table(
        [
            [_cell("merged", rowspan=2), _cell("top")],
            [_cell("ignored", invisible=True), _cell("bottom")],
        ]
    )
    result = dedoc_table_to_html(table)

    assert '<td rowspan="2">merged</td><td>top</td>' in result
    assert "<td>bottom</td>" in result
    assert "<!-- merged" not in result


def test_dedoc_table_to_html_fail_fast_on_invalid_spans() -> None:
    table = _table([[_cell("bad", rowspan=0, colspan=1)]])
    with pytest.raises(ValueError, match="invalid cell span"):
        dedoc_table_to_html(table)
