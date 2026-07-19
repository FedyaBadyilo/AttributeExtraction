from research.steps.chunking.domain.models import TableSeam
from research.steps.chunking.domain.splitters import split_structure_text, split_table_html
from research.steps.merge.domain.context_merge import IndexedSplit, _join_splits_with_header_dedup

SAMPLE_TABLE = (
    "<table>"
    "<tr><td>col1</td><td>col2</td></tr>"
    "<tr><td>a</td><td>b</td></tr>"
    "<tr><td>c</td><td>d</td></tr>"
    "<tr><td>e</td><td>f</td></tr>"
    "</table>"
)

HEADER = "<tr><td>col1</td><td>col2</td></tr>"


def _char_count(text: str) -> int:
    return len(text)


def _join_parts(parts: list) -> str:
    splits = [
        IndexedSplit(
            table_chunk_index=i,
            point_id=i,
            content=part.content,
            seam_to_next=part.seam_to_next,
        )
        for i, part in enumerate(parts)
    ]
    text, _ = _join_splits_with_header_dedup(splits)
    return text


def test_split_table_html_keeps_small_table_intact() -> None:
    parts = split_table_html(SAMPLE_TABLE, max_tokens=10_000, length_function=_char_count)
    assert len(parts) == 1
    assert parts[0].content == SAMPLE_TABLE
    assert parts[0].seam_to_next is None


def test_split_table_html_repeats_header() -> None:
    # header + one data row is 79 chars; force split after each data row
    parts = split_table_html(SAMPLE_TABLE, max_tokens=79, length_function=_char_count)
    assert len(parts) == 3
    for i, part in enumerate(parts):
        assert part.content.startswith("<table>" + HEADER)
        assert part.content.endswith("</table>")
        assert part.content.count("<tr>") == 2
        if i < len(parts) - 1:
            assert part.seam_to_next == TableSeam(kind="row")
        else:
            assert part.seam_to_next is None


def test_split_table_html_keeps_rowspan_atom_together() -> None:
    table = (
        "<table>"
        "<tr><td>h1</td><td>h2</td></tr>"
        "<tr><td rowspan=\"2\">ab</td><td>r1</td></tr>"
        "<tr><td>r2</td></tr>"
        "<tr><td>c</td><td>d</td></tr>"
        "</table>"
    )
    header = "<tr><td>h1</td><td>h2</td></tr>"
    rowspan_pair = (
        '<tr><td rowspan="2">ab</td><td>r1</td></tr>'
        "<tr><td>r2</td></tr>"
    )
    # Fits header + rowspan atom, but not header + atom + last row
    atom_len = len("<table>" + header + rowspan_pair + "</table>")
    parts = split_table_html(table, max_tokens=atom_len, length_function=_char_count)
    assert len(parts) == 2
    assert rowspan_pair in parts[0].content
    assert "<tr><td>c</td><td>d</td></tr>" in parts[1].content
    assert parts[0].content.startswith("<table>" + header)
    assert parts[1].content.startswith("<table>" + header)
    assert parts[0].seam_to_next == TableSeam(kind="row")
    assert parts[1].seam_to_next is None


def test_split_table_html_mid_cell_on_oversized_row() -> None:
    table = (
        "<table>"
        "<tr><td>h</td></tr>"
        "<tr><td>this-row-is-intentionally-long-xxxxxxxx</td></tr>"
        "<tr><td>short</td></tr>"
        "</table>"
    )
    header = "<tr><td>h</td></tr>"
    long_row = "<tr><td>this-row-is-intentionally-long-xxxxxxxx</td></tr>"
    one = "<table>" + header + long_row + "</table>"
    parts = split_table_html(
        table,
        max_tokens=len(one) - 1,
        length_function=_char_count,
        table_uid="t-uid",
    )
    assert len(parts) >= 2
    assert all(p.content.startswith("<table>" + header) for p in parts)
    assert parts[0].seam_to_next is not None
    assert parts[0].seam_to_next.kind == "cell"
    assert parts[0].seam_to_next.cell_col == 0
    # Last data row may be in its own part after cell fragments
    joined = _join_parts(parts)
    assert "this-row-is-intentionally-long-xxxxxxxx" in joined
    assert "<tr><td>short</td></tr>" in joined
    assert joined.count("<table>") == 1


def test_split_table_html_mid_span_on_oversized_rowspan_atom() -> None:
    table = (
        "<table>"
        "<tr><td>h1</td><td>h2</td></tr>"
        "<tr><td rowspan=\"3\">big</td><td>r1</td></tr>"
        "<tr><td>r2</td></tr>"
        "<tr><td>r3</td></tr>"
        "</table>"
    )
    header = "<tr><td>h1</td><td>h2</td></tr>"
    atom = (
        '<tr><td rowspan="3">big</td><td>r1</td></tr>'
        "<tr><td>r2</td></tr>"
        "<tr><td>r3</td></tr>"
    )
    atom_len = len("<table>" + header + atom + "</table>")
    parts = split_table_html(
        table,
        max_tokens=atom_len - 1,
        length_function=_char_count,
        table_uid="t-uid",
    )
    assert len(parts) >= 2
    assert any(p.seam_to_next is not None and p.seam_to_next.kind == "span" for p in parts[:-1]) or any(
        p.seam_to_next is not None and p.seam_to_next.kind == "cell" for p in parts[:-1]
    )
    joined = _join_parts(parts)
    assert joined.count("<table>") == 1
    assert 'rowspan="3"' in joined
    assert "<tr><td>r2</td></tr>" in joined
    assert "<tr><td>r3</td></tr>" in joined


def test_split_table_html_mid_cell_roundtrip_notes_style() -> None:
    notes = (
        "Notes: 1. First sentence here. 2. Second sentence continues. "
        "3. Third sentence finishes the cell."
    )
    table = (
        "<table>"
        "<tr><td>h</td></tr>"
        f"<tr><td colspan=\"2\">{notes}</td></tr>"
        "</table>"
    )
    full_len = _char_count(table)
    # Force mid-cell: budget just under full table
    parts = split_table_html(table, max_tokens=full_len - 10, length_function=_char_count)
    assert len(parts) >= 2
    assert parts[0].seam_to_next is not None
    assert parts[0].seam_to_next.kind == "cell"
    joined = _join_parts(parts)
    assert notes in joined
    assert joined.count("<table>") == 1


def test_split_table_html_demotes_oversized_header_then_mid_cell() -> None:
    """Title-like tables put fat text in row 0; demote header and mid-cell it."""
    fat = "Title block. " * 40  # long header cell
    table = (
        "<table>"
        f"<tr><td></td><td></td><td rowspan=\"2\">{fat}</td></tr>"
        "<tr><td></td><td></td></tr>"
        "</table>"
    )
    header_only = "<table>" + f"<tr><td></td><td></td><td rowspan=\"2\">{fat}</td></tr>" + "</table>"
    assert _char_count(header_only) > 200
    parts = split_table_html(table, max_tokens=200, length_function=_char_count)
    assert len(parts) >= 2
    assert any(p.seam_to_next and p.seam_to_next.kind == "cell" for p in parts[:-1])
    joined = _join_parts(parts)
    assert fat in joined
    assert all(_char_count(p.content) <= 200 for p in parts)

    text = "alpha. beta; gamma\ndelta"
    parts = split_structure_text(text, max_tokens=10, length_function=_char_count)
    assert len(parts) >= 2


def test_split_table_html_mid_cols_on_wide_row() -> None:
    """Many short cells: row skeleton exceeds budget → cols seams; stitch is lossless."""
    cells = "".join(f"<td>c{i}</td>" for i in range(12))
    table = f"<table><tr><td>h</td></tr><tr>{cells}</tr></table>"
    wide_row = f"<tr>{cells}</tr>"
    one = "<table><tr><td>h</td></tr>" + wide_row + "</table>"
    # Budget fits header + a few cells, but not the full wide row.
    max_tokens = len("<table><tr><td>h</td></tr><tr><td>c0</td><td>c1</td><td>c2</td></tr></table>")
    assert _char_count(one) > max_tokens
    parts = split_table_html(table, max_tokens=max_tokens, length_function=_char_count)
    assert len(parts) >= 2
    assert any(p.seam_to_next and p.seam_to_next.kind == "cols" for p in parts[:-1])
    assert all(_char_count(p.content) <= max_tokens for p in parts)
    joined = _join_parts(parts)
    assert joined.count("<table>") == 1
    for i in range(12):
        assert f"<td>c{i}</td>" in joined


def test_split_table_html_mid_cols_when_empty_wrap_equals_budget() -> None:
    """Empty-longest wrap == max_tokens must fall through to mid-cols, not fail mid-cell."""
    header_cells = "".join(f"<td>H{i}</td>" for i in range(8))
    # Wide data row: emptying the longest cell lands exactly on the budget.
    data_cells = "".join(f"<td>d{i}</td>" for i in range(7)) + "<td>VALUE</td>"
    table = f"<table><tr>{header_cells}</tr><tr>{data_cells}</tr></table>"
    empty_longest = (
        f"<table><tr>{header_cells}</tr><tr>"
        + "".join(f"<td>d{i}</td>" for i in range(7))
        + "<td></td></tr></table>"
    )
    max_tokens = _char_count(empty_longest)
    assert _char_count(table) > max_tokens
    parts = split_table_html(table, max_tokens=max_tokens, length_function=_char_count)
    assert len(parts) >= 2
    assert any(p.seam_to_next and p.seam_to_next.kind == "cols" for p in parts[:-1])
    assert all(_char_count(p.content) <= max_tokens for p in parts)
    joined = _join_parts(parts)
    assert "VALUE" in joined
    for i in range(7):
        assert f"d{i}" in joined


def test_split_table_html_mid_cols_demoted_wide_header_row() -> None:
    """Wide first row demotes, then mid-cols without failing."""
    cells = "".join(f"<td>v{i}</td>" for i in range(20))
    table = f"<table><tr>{cells}</tr><tr><td>x</td></tr></table>"
    header_only = f"<table><tr>{cells}</tr></table>"
    max_tokens = len("<table><tr></tr><tr><td>v0</td><td>v1</td><td>v2</td><td>v3</td></tr></table>")
    assert _char_count(header_only) > max_tokens
    parts = split_table_html(table, max_tokens=max_tokens, length_function=_char_count)
    assert len(parts) >= 2
    assert any(p.seam_to_next and p.seam_to_next.kind == "cols" for p in parts[:-1])
    assert all(_char_count(p.content) <= max_tokens for p in parts)
    joined = _join_parts(parts)
    for i in range(20):
        assert f"v{i}" in joined
    assert "x" in joined
