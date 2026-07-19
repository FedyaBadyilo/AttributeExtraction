"""Canonical Markdown contract for the document parsing benchmark."""

from research.benchmarks.document_parsing.canonicalize.markdown import (
    CANONICALIZATION_VERSION,
    HtmlTable,
    HtmlTableCell,
    canonicalize_ground_truth,
    canonicalize_pair,
    find_html_table_spans,
    markdown_to_plain_text,
    normalize_cell_text,
    normalize_inline_text,
    normalize_unicode,
    parse_html_table_fragment,
    parse_html_tables,
    render_html_table,
)

__all__ = [
    "CANONICALIZATION_VERSION",
    "HtmlTable",
    "HtmlTableCell",
    "canonicalize_ground_truth",
    "canonicalize_pair",
    "find_html_table_spans",
    "markdown_to_plain_text",
    "normalize_cell_text",
    "normalize_inline_text",
    "normalize_unicode",
    "parse_html_table_fragment",
    "parse_html_tables",
    "render_html_table",
]
