"""Offline text-metric tests."""

from __future__ import annotations

import pytest

from research.benchmarks.document_parsing.scoring import score_text


def test_perfect_match_after_canonicalization() -> None:
    pred = "# **Елка**\n\n<table><tr><td>A</td></tr><tr><td>B</td></tr></table>"
    gt = "# Ёлка\n\n<table><tr><td>A</td></tr><tr><td>B</td></tr></table>"

    scores = score_text(pred, gt)

    assert scores.cer == 1.0
    assert scores.wer == 1.0
    assert scores.token_f1 == 1.0


def test_single_word_typo() -> None:
    scores = score_text("bat", "cat")

    assert scores.cer == pytest.approx(2 / 3)
    assert scores.wer == 0.0
    assert scores.token_f1 == 0.0


@pytest.mark.parametrize(
    ("pred", "gt", "expected"),
    [
        ("", "", (1.0, 1.0, 1.0)),
        ("x", "", (0.0, 0.0, 0.0)),
        ("", "x", (0.0, 0.0, 0.0)),
    ],
)
def test_empty_input_semantics(
    pred: str,
    gt: str,
    expected: tuple[float, float, float],
) -> None:
    scores = score_text(pred, gt)

    assert (scores.cer, scores.wer, scores.token_f1) == expected


def test_token_f1_is_multiset_bag_of_words() -> None:
    scores = score_text("a b b", "a a b")

    assert scores.token_precision == pytest.approx(2 / 3)
    assert scores.token_recall == pytest.approx(2 / 3)
    assert scores.token_f1 == pytest.approx(2 / 3)


def test_wer_above_one_clamps_to_zero() -> None:
    scores = score_text("one two three four five six", "one")

    assert scores.wer == 0.0


def test_table_whitespace_is_flattened_for_text_metrics() -> None:
    pred = "<table><tr><td>key</td><td>line 1 line 2</td></tr></table>"
    gt = "<table><tr><td>key</td><td>line 1<br>line 2</td></tr></table>"

    scores = score_text(pred, gt)

    assert scores.cer == 1.0
    assert scores.wer == 1.0
    assert scores.token_f1 == 1.0
