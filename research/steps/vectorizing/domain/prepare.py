"""Prepare chunk text for dense and BM25 indexing."""

from __future__ import annotations

import html
import re

from research.steps.common.downstream_text import remove_placeholder_blocks

_RE_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_RE_ITALIC = re.compile(r"\*(.+?)\*", re.DOTALL)
_RE_HEADER_PREFIX = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_RE_TABLE = re.compile(r"<table\b[^>]*>.*?</table>", re.IGNORECASE | re.DOTALL)
_RE_TR = re.compile(r"<tr\b[^>]*>.*?</tr>", re.IGNORECASE | re.DOTALL)
_RE_CELL = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)
_RE_TAG = re.compile(r"<[^>]+>")


def _html_table_to_cell_text(table_html: str) -> str:
    """Extract cell texts only: space between cells, newline between rows."""
    rows: list[str] = []
    for row_html in _RE_TR.findall(table_html):
        cells: list[str] = []
        for inner in _RE_CELL.findall(row_html):
            text = html.unescape(_RE_TAG.sub("", inner)).strip()
            if text:
                cells.append(text)
        if cells:
            rows.append(" ".join(cells))
    return "\n".join(rows)


def _replace_html_tables_with_cell_text(content: str) -> str:
    if "<table" not in content.lower():
        return content
    return _RE_TABLE.sub(lambda m: _html_table_to_cell_text(m.group(0)), content)


def strip_markdown_for_indexing(content: str) -> str:
    """Remove markdown symbols and HTML table markup from chunk content for indexing."""
    content = remove_placeholder_blocks(content)
    content = _replace_html_tables_with_cell_text(content)
    content = _RE_BOLD.sub(r"\1", content)
    content = _RE_ITALIC.sub(r"\1", content)
    content = _RE_HEADER_PREFIX.sub("", content)
    return content


def add_header_path_prefix(content: str, header_path: list[str]) -> str:
    """Prefix content with header path for better retrieval context."""
    path_str = " -> ".join(header_path)
    return f"[{path_str}]\n{content}"


def prepare_content_for_indexing(content: str, header_path: list[str]) -> str:
    """Clean markdown then add header path prefix. Used for dense + BM25 vectors only."""
    return add_header_path_prefix(strip_markdown_for_indexing(content), header_path)
