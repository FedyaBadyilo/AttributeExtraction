"""Backend-independent Markdown scoring API."""

from research.benchmarks.document_parsing.scoring.fallback import (
    demote_html_tables_to_text,
    prediction_for_scoring,
)
from research.benchmarks.document_parsing.scoring.models import (
    CountComparison,
    DocumentScores,
    SequenceScores,
    StructuralCountScores,
    StructureScores,
    TablePairScore,
    TableScores,
    TextScores,
)
from research.benchmarks.document_parsing.scoring.structure import score_structure
from research.benchmarks.document_parsing.scoring.tables import (
    markdown_tables_to_html,
    score_tables,
)
from research.benchmarks.document_parsing.scoring.text import score_text

METRIC_CONTRACT_VERSION = "2.0"


def score_prepared_document(
    scoring_pred: str,
    gt_markdown: str,
    *,
    table_parse_error: str | None = None,
) -> DocumentScores:
    """Score already-prepared pred Markdown (strict-canonicalizable against GT)."""
    return DocumentScores(
        text=score_text(scoring_pred, gt_markdown),
        tables=score_tables(scoring_pred, gt_markdown),
        structure=score_structure(scoring_pred, gt_markdown),
        table_parse_error=table_parse_error,
    )


def score_document(pred_markdown: str, gt_markdown: str) -> DocumentScores:
    """Score pred/GT hybrid Markdown with HTML tables.

    Malformed pred HTML tables are demoted to plain text, then scored normally
    (missing tables → TEDS 0). ``table_parse_error`` records the demotion.
    """
    scoring_pred, table_parse_error = prediction_for_scoring(pred_markdown, gt_markdown)
    return score_prepared_document(
        scoring_pred,
        gt_markdown,
        table_parse_error=table_parse_error,
    )


__all__ = [
    "METRIC_CONTRACT_VERSION",
    "CountComparison",
    "DocumentScores",
    "SequenceScores",
    "StructuralCountScores",
    "StructureScores",
    "TablePairScore",
    "TableScores",
    "TextScores",
    "demote_html_tables_to_text",
    "markdown_tables_to_html",
    "prediction_for_scoring",
    "score_document",
    "score_prepared_document",
    "score_structure",
    "score_tables",
    "score_text",
]
