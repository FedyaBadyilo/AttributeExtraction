"""Tests for split scoring when prediction HTML tables are malformed."""

from __future__ import annotations

from research.benchmarks.document_parsing.scoring import score_document


def test_malformed_pred_still_scores_text_and_zeros_tables() -> None:
    pred = "<table><tr><td>Pos</td><td>Name</td><td>Type</td></tr><tr><td>1</td><td>item</td></tr>"
    gt = (
        "<table><tr><td>Pos</td><td>Name</td><td>Type</td><td>Code</td><td>Qty</td></tr>"
        "<tr><td>1</td><td>item</td><td>mark</td><td>c</td><td>1</td></tr></table>"
    )

    scores = score_document(pred, gt)

    assert scores.table_parse_error is not None
    assert "Unclosed" in scores.table_parse_error
    assert scores.text.token_f1 > 0.0
    assert scores.tables.teds == 0.0
    assert scores.tables.gt_count == 1


def test_valid_tables_leave_table_parse_error_unset() -> None:
    md = "<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>"
    scores = score_document(md, md)
    assert scores.table_parse_error is None
    assert scores.tables.teds == 1.0
    assert scores.text.token_f1 == 1.0


def test_ragged_grid_pred_is_demoted() -> None:
    pred = (
        '<table><tr><td rowspan="2">A</td><td>B</td></tr>'
        "<tr><td>C</td><td>extra</td></tr></table>"
    )
    gt = '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'

    scores = score_document(pred, gt)

    assert scores.table_parse_error is not None
    assert scores.tables.pred_count == 0
    assert scores.tables.gt_count == 1
    assert scores.tables.teds == 0.0


def test_rowspan_past_declared_rows_pred_is_demoted() -> None:
    pred = (
        '<table><tr><td rowspan="3">A</td><td>B</td></tr>'
        "<tr><td>C</td></tr></table>"
    )
    gt = '<table><tr><td rowspan="2">A</td><td>B</td></tr><tr><td>C</td></tr></table>'

    scores = score_document(pred, gt)

    assert scores.table_parse_error is not None
    assert "rowspan extends past" in scores.table_parse_error
    assert scores.tables.pred_count == 0
    assert scores.tables.gt_count == 1
    assert scores.tables.teds == 0.0
