"""Offline table-metric tests for HTML tables with native spans."""

from __future__ import annotations

import pytest

from research.benchmarks.document_parsing.scoring import (
    markdown_tables_to_html,
    score_tables,
)


def test_perfect_html_table_match() -> None:
    md = "<table><tr><td>A</td><td>B</td></tr><tr><td>x</td><td>y</td></tr></table>"

    scores = score_tables(md, md)

    assert scores.pred_count == scores.gt_count == 1
    assert scores.teds == 1.0
    assert scores.teds_structure == 1.0
    assert scores.pairs[0].pred_present
    assert scores.pairs[0].gt_present


def test_cell_typo_changes_teds_but_not_teds_structure() -> None:
    pred = "<table><tr><td>A</td></tr><tr><td>typo</td></tr></table>"
    gt = "<table><tr><td>A</td></tr><tr><td>value</td></tr></table>"

    scores = score_tables(pred, gt)

    assert 0.0 < scores.teds < 1.0
    assert scores.teds_structure == 1.0


def test_spans_are_scored_not_flattened() -> None:
    spanned = (
        '<table><tr><td rowspan="2">A</td><td>B</td></tr>'
        "<tr><td>C</td></tr></table>"
    )
    flattened = (
        "<table><tr><td>A</td><td>B</td></tr>"
        "<tr><td>A</td><td>C</td></tr></table>"
    )

    same = score_tables(spanned, spanned)
    vs_flat = score_tables(spanned, flattened)

    assert same.teds == 1.0
    assert same.teds_structure == 1.0
    assert vs_flat.teds < 1.0
    assert vs_flat.teds_structure < 1.0
    assert 'rowspan="2"' in markdown_tables_to_html(spanned)[0]


def test_br_is_collapsed_so_multiline_matches_spaced_text() -> None:
    pred = "<table><tr><td>key</td><td>line 1 line 2</td></tr></table>"
    gt = "<table><tr><td>key</td><td>line 1<br>line 2</td></tr></table>"

    scores = score_tables(pred, gt)

    assert scores.teds == 1.0
    assert scores.teds_structure == 1.0
    assert "<br" not in markdown_tables_to_html(gt)[0]


def test_missing_table_adds_zero_positional_slot() -> None:
    first = "<table><tr><td>A</td></tr><tr><td>x</td></tr></table>"
    second = "<table><tr><td>B</td></tr><tr><td>y</td></tr></table>"

    scores = score_tables(first, first + "\n\n" + second)

    assert scores.pred_count == 1
    assert scores.gt_count == 2
    assert len(scores.pairs) == 2
    assert scores.pairs[0].teds == 1.0
    assert scores.pairs[1].teds == 0.0
    assert not scores.pairs[1].pred_present
    assert scores.teds == pytest.approx(0.5)
    assert scores.teds_structure == pytest.approx(0.5)


def test_extra_table_adds_zero_positional_slot() -> None:
    first = "<table><tr><td>A</td></tr></table>"
    second = "<table><tr><td>B</td></tr></table>"

    scores = score_tables(first + "\n\n" + second, first)

    assert scores.pred_count == 2
    assert scores.gt_count == 1
    assert scores.pairs[1].pred_present
    assert not scores.pairs[1].gt_present
    assert scores.teds == pytest.approx(0.5)


def test_no_tables_is_perfect_not_zero() -> None:
    scores = score_tables("plain prediction", "plain reference")

    assert scores.pred_count == scores.gt_count == 0
    assert scores.pairs == []
    assert scores.teds == 1.0
    assert scores.teds_structure == 1.0


def test_html_conversion_escapes_literal_markup() -> None:
    converted = markdown_tables_to_html("<table><tr><td>a < b</td><td>x & y</td></tr></table>")[0]

    assert "a &lt; b" in converted
    assert "x &amp; y" in converted
    assert converted.startswith("<html><body><table>")
