"""Offline structural-metric tests."""

from __future__ import annotations

import pytest

from research.benchmarks.document_parsing.scoring import score_structure


def test_perfect_structure_scores() -> None:
    markdown = "# A\n\nParagraph\n\n- one\n- two\n\n<table><tr><td>H</td></tr><tr><td>x</td></tr></table>"

    scores = score_structure(markdown, markdown)

    assert scores.counts.similarity == 1.0
    assert scores.headings.f1 == 1.0
    assert scores.ast_similarity == 1.0


def test_count_similarity_uses_min_over_max() -> None:
    pred = (
        "# A\n# B\n# C\n\n"
        "<table><tr><td>H</td></tr><tr><td>x</td></tr><tr><td>y</td></tr></table>"
    )
    gt = "# A\n# B\n\n<table><tr><td>H</td></tr><tr><td>x</td></tr></table>"

    scores = score_structure(pred, gt)

    level_one = scores.counts.heading_levels[1]
    assert level_one.pred == 3
    assert level_one.gt == 2
    assert level_one.delta == 1
    assert level_one.similarity == pytest.approx(2 / 3)
    assert scores.counts.data_rows.pred == 3
    assert scores.counts.data_rows.gt == 2
    assert scores.counts.data_rows.similarity == pytest.approx(2 / 3)


def test_heading_sequence_f1_uses_ordered_lcs() -> None:
    pred = "# B\n\ntext\n\n# A"
    gt = "# A\n\ntext\n\n# B"

    scores = score_structure(pred, gt)

    assert scores.headings.pred_count == 2
    assert scores.headings.gt_count == 2
    assert scores.headings.lcs_length == 1
    assert scores.headings.precision == 0.5
    assert scores.headings.recall == 0.5
    assert scores.headings.f1 == 0.5


def test_heading_match_includes_level_and_normalized_title() -> None:
    scores = score_structure("# **Ёлка**", "## Елка")

    assert scores.headings.lcs_length == 0
    assert scores.headings.f1 == 0.0


def test_ast_ignores_all_leaf_text() -> None:
    pred = "# Completely different\n\nDifferent paragraph\n\n<table><tr><td>X</td></tr><tr><td>y</td></tr></table>"
    gt = "# Title\n\nBody\n\n<table><tr><td>Header</td></tr><tr><td>value</td></tr></table>"

    scores = score_structure(pred, gt)

    assert scores.ast_similarity == 1.0
    assert scores.headings.f1 == 0.0


def test_ast_penalizes_structure_changes() -> None:
    scores = score_structure("- item one\n- item two", "A paragraph")

    assert scores.ast_similarity < 1.0


def test_ast_recognizes_hierarchical_numbered_list_markers() -> None:
    numbered = score_structure("1.2 First\n1.3 Second", "1.2 Other\n1.3 Values")
    paragraph = score_structure("1.2 First\n1.3 Second", "A paragraph")

    assert numbered.ast_similarity == 1.0
    assert paragraph.ast_similarity < 1.0


def test_ast_encodes_cell_spans() -> None:
    spanned = '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'
    rectangular = (
        "<table><tr><td>A</td><td>B</td></tr><tr><td>A</td><td>C</td></tr></table>"
    )

    same = score_structure(spanned, spanned)
    mismatch = score_structure(spanned, rectangular)

    assert same.ast_similarity == 1.0
    assert mismatch.ast_similarity < 1.0


def test_all_table_rows_count_as_data_rows() -> None:
    table = "<table><tr><td>a</td><td>b</td></tr><tr><td>c</td><td>d</td></tr></table>"

    scores = score_structure(table, table)

    assert scores.counts.data_rows.pred == 2
    assert scores.counts.data_rows.gt == 2


def test_no_headings_has_perfect_heading_f1() -> None:
    scores = score_structure("paragraph", "different paragraph")

    assert scores.headings.precision == 1.0
    assert scores.headings.recall == 1.0
    assert scores.headings.f1 == 1.0
