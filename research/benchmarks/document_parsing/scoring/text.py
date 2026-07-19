"""Document-level text metrics over Markdown strings."""

from __future__ import annotations

from collections import Counter

import jiwer

from research.benchmarks.document_parsing.canonicalize import (
    canonicalize_pair,
    markdown_to_plain_text,
)
from research.benchmarks.document_parsing.scoring.models import TextScores


def _multiset_token_scores(pred_text: str, gt_text: str) -> tuple[float, float, float]:
    pred = Counter(pred_text.split())
    gt = Counter(gt_text.split())
    overlap = sum((pred & gt).values())
    pred_count = sum(pred.values())
    gt_count = sum(gt.values())
    if pred_count == 0 and gt_count == 0:
        return 1.0, 1.0, 1.0
    precision = overlap / pred_count if pred_count else 0.0
    recall = overlap / gt_count if gt_count else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def _accuracy_from_error_rate(error_rate: float) -> float:
    return max(0.0, 1.0 - error_rate)


def score_text(pred_markdown: str, gt_markdown: str) -> TextScores:
    """Score all visible Markdown text, including table cells, in reading order."""
    canonical_pred, canonical_gt = canonicalize_pair(pred_markdown, gt_markdown)
    pred_text = markdown_to_plain_text(canonical_pred)
    gt_text = markdown_to_plain_text(canonical_gt)
    precision, recall, f1 = _multiset_token_scores(pred_text, gt_text)
    return TextScores(
        cer=_accuracy_from_error_rate(float(jiwer.cer(gt_text, pred_text))),
        wer=_accuracy_from_error_rate(float(jiwer.wer(gt_text, pred_text))),
        token_precision=precision,
        token_recall=recall,
        token_f1=f1,
    )
