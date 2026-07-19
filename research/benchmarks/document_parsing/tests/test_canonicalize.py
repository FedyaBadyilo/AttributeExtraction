"""Offline tests for the v2 hybrid Markdown + HTML table contract."""

from __future__ import annotations

import pytest

from research.benchmarks.document_parsing.canonicalize import (
    CANONICALIZATION_VERSION,
    canonicalize_ground_truth,
    canonicalize_pair,
    markdown_to_plain_text,
    parse_html_tables,
    render_html_table,
)


def test_canonicalization_version_is_html_contract() -> None:
    assert CANONICALIZATION_VERSION == "2.0"


def test_plain_text_normalizes_unicode_wrappers_and_attachments() -> None:
    markdown = (
        "# **Ёлка**\n\n"
        "- [ссылка](https://example.test) и `Ａ`\n"
        "<attachment uid='image-1'>\n"
    )

    assert markdown_to_plain_text(markdown) == "Елка ссылка и A"


def test_html_table_round_trip_is_deterministic() -> None:
    markdown = (
        "# Title\n\n"
        '<table><tr><td rowspan="2">A</td><td>B</td></tr>'
        "<tr><td>C</td></tr></table>\n\n"
        "tail"
    )

    canonical = canonicalize_ground_truth(markdown)
    table = parse_html_tables(canonical)[0]

    assert canonical == canonicalize_ground_truth(canonical)
    assert render_html_table(table) == (
        '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'
    )
    assert table.rows[0][0].rowspan == 2
    assert table.data_row_count == 2


def test_canonicalize_normalizes_th_thead_br_and_entities() -> None:
    raw = (
        "<table><thead><tr><th>A &amp; B</th><th>x<br/>y</th></tr></thead>"
        "<tbody><tr><td></td><td>  z  </td></tr></tbody></table>"
    )

    canonical = canonicalize_ground_truth(raw)

    assert canonical == (
        "<table><tr><td>A &amp; B</td><td>x y</td></tr>"
        "<tr><td></td><td>z</td></tr></table>"
    )
    assert "<th" not in canonical
    assert "thead" not in canonical
    assert "<br" not in canonical


def test_plain_text_includes_html_table_cells_in_reading_order() -> None:
    markdown = "# H\n\n<table><tr><td>Ключ</td><td>строка 1   строка 2</td></tr><tr><td>x</td><td>y</td></tr></table>"

    assert markdown_to_plain_text(markdown) == "H Ключ строка 1 строка 2 x y"


def test_origin_only_spans_are_kept_not_flattened() -> None:
    markdown = '<table><tr><td colspan="2">wide</td></tr><tr><td>a</td><td>b</td></tr></table>'

    table = parse_html_tables(canonicalize_ground_truth(markdown))[0]

    assert len(table.rows[0]) == 1
    assert table.rows[0][0].colspan == 2
    assert table.rows[0][0].text == "wide"


def test_overlapping_spans_fail_fast() -> None:
    markdown = (
        '<table><tr><td rowspan="2">A</td><td>B</td></tr>'
        "<tr><td>C</td><td>extra</td></tr></table>"
    )

    with pytest.raises(ValueError, match="ragged|overlapping|gapped"):
        canonicalize_ground_truth(markdown)


def test_unclosed_table_fails_fast() -> None:
    with pytest.raises(ValueError, match="Unclosed"):
        canonicalize_ground_truth("<table><tr><td>a</td></tr>")


def test_pipe_markdown_is_not_parsed_as_a_table() -> None:
    markdown = "| A | B |\n| --- | --- |\n| x | y |"

    assert parse_html_tables(markdown) == []
    assert "table" not in canonicalize_ground_truth(markdown).lower()
    assert markdown_to_plain_text(markdown) == "| A | B | | --- | --- | | x | y |"


def test_canonicalize_pair_is_symmetric() -> None:
    pred = "# **Ёлка**\n<table><tr><td>a</td></tr></table>"
    gt = "# Елка\n<table><tr><td>a</td></tr></table>"

    canonical_pred, canonical_gt = canonicalize_pair(pred, gt)

    assert canonical_pred == canonical_gt
