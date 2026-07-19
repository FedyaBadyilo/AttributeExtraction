"""HTML-table conversion and positional TEDS scoring (native spans)."""

from __future__ import annotations

from table_recognition_metric import TEDS

from research.benchmarks.document_parsing.canonicalize import (
    HtmlTable,
    canonicalize_ground_truth,
    canonicalize_pair,
    parse_html_tables,
    render_html_table,
)
from research.benchmarks.document_parsing.scoring.models import (
    TablePairScore,
    TableScores,
)


def table_to_teds_html(table: HtmlTable) -> str:
    """Wrap a contract HTML table for ``table_recognition_metric.TEDS``."""
    return f"<html><body>{render_html_table(table)}</body></html>"


def markdown_tables_to_html(markdown: str) -> list[str]:
    """Convert every HTML table in Markdown to TEDS-compatible HTML documents."""
    canonical = canonicalize_ground_truth(markdown)
    return [table_to_teds_html(table) for table in parse_html_tables(canonical)]


def _bounded(score: float) -> float:
    return max(0.0, min(1.0, float(score)))


def score_tables(pred_markdown: str, gt_markdown: str) -> TableScores:
    """Score tables positionally; every missing or extra slot contributes zero."""
    canonical_pred, canonical_gt = canonicalize_pair(pred_markdown, gt_markdown)
    pred_tables = parse_html_tables(canonical_pred)
    gt_tables = parse_html_tables(canonical_gt)
    slot_count = max(len(pred_tables), len(gt_tables))
    if slot_count == 0:
        return TableScores(
            pred_count=0,
            gt_count=0,
            pairs=[],
            teds=1.0,
            teds_structure=1.0,
        )

    content_metric = TEDS(structure_only=False)
    structure_metric = TEDS(structure_only=True)
    pairs: list[TablePairScore] = []
    for position in range(slot_count):
        pred_present = position < len(pred_tables)
        gt_present = position < len(gt_tables)
        if pred_present and gt_present:
            pred_html = table_to_teds_html(pred_tables[position])
            gt_html = table_to_teds_html(gt_tables[position])
            teds = _bounded(content_metric(pred_html, gt_html))
            teds_structure = _bounded(structure_metric(pred_html, gt_html))
        else:
            teds = 0.0
            teds_structure = 0.0
        pairs.append(
            TablePairScore(
                position=position,
                pred_present=pred_present,
                gt_present=gt_present,
                teds=teds,
                teds_structure=teds_structure,
            )
        )

    return TableScores(
        pred_count=len(pred_tables),
        gt_count=len(gt_tables),
        pairs=pairs,
        teds=sum(pair.teds for pair in pairs) / slot_count,
        teds_structure=sum(pair.teds_structure for pair in pairs) / slot_count,
    )
