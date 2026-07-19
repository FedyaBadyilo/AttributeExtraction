"""Helpers when prediction Markdown fails the strict HTML-table parser."""

from __future__ import annotations

import re

from research.benchmarks.document_parsing.canonicalize import (
    canonicalize_pair,
    find_html_table_spans,
    normalize_cell_text,
    normalize_inline_text,
    normalize_unicode,
    parse_html_table_fragment,
)

_TABLE_FORMAT_ERROR_MARKERS = (
    "Unclosed HTML table",
    "Nested HTML tables",
    "Malformed HTML table",
    "HTML table has",
    "HTML table rowspan",
    "invalid cell",
    "overlapping spans",
)
_TABLE_OPEN_RE = re.compile(r"<table\b[^>]*>", re.IGNORECASE)
_TABLE_CLOSE_RE = re.compile(r"</table\s*>", re.IGNORECASE)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ROW_CELL_TAG_RE = re.compile(
    r"</?(?:tr|td|th|thead|tbody|tfoot)\b[^>]*>",
    re.IGNORECASE,
)


def is_table_format_error(exc: BaseException) -> bool:
    message = str(exc)
    return any(marker in message for marker in _TABLE_FORMAT_ERROR_MARKERS)


def _strip_table_markup(fragment: str) -> str:
    stripped = _TABLE_OPEN_RE.sub("", fragment)
    stripped = _TABLE_CLOSE_RE.sub("", stripped)
    stripped = _ROW_CELL_TAG_RE.sub(" ", stripped)
    return normalize_cell_text(_BR_RE.sub(" ", stripped))


def demote_html_tables_to_text(markdown: str) -> str:
    """Replace ``<table>…</table>`` blocks with visible cell text."""
    source = normalize_unicode(markdown).replace("\r\n", "\n").replace("\r", "\n")
    try:
        spans = find_html_table_spans(source)
    except ValueError:
        return _strip_table_markup(source)

    if not spans:
        return source

    chunks: list[str] = []
    cursor = 0
    for start, end in spans:
        chunks.append(source[cursor:start])
        fragment = source[start:end]
        try:
            rows = parse_html_table_fragment(fragment)
            cell_texts = [
                text
                for row in rows
                for cell in row
                if (text := normalize_inline_text(cell.text))
            ]
            chunks.append(" ".join(cell_texts))
        except ValueError:
            stripped = _strip_table_markup(fragment)
            if stripped:
                chunks.append(stripped)
        cursor = end
    chunks.append(source[cursor:])
    return "".join(chunks)


def prediction_for_scoring(pred_markdown: str, gt_markdown: str) -> tuple[str, str | None]:
    """Return ``(pred_used_for_metrics, table_parse_error_or_none)``."""
    try:
        canonicalize_pair(pred_markdown, gt_markdown)
    except ValueError as exc:
        if not is_table_format_error(exc):
            raise
        return demote_html_tables_to_text(pred_markdown), str(exc)
    return pred_markdown, None


__all__ = [
    "demote_html_tables_to_text",
    "is_table_format_error",
    "prediction_for_scoring",
]
