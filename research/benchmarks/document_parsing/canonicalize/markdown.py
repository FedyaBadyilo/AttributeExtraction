"""Backend-independent canonicalization for hybrid Markdown + HTML tables."""

from __future__ import annotations

import html
import re
import unicodedata
from html.parser import HTMLParser

from pydantic import BaseModel, ConfigDict, Field

CANONICALIZATION_VERSION = "2.0"

_ATTACHMENT_RE = re.compile(r"<attachment\b[^>]*>", re.IGNORECASE)
_UNRESOLVED_TABLE_RE = re.compile(r"<table\b[^>]*\buid\s*=", re.IGNORECASE)
_TABLE_OPEN_RE = re.compile(r"<table\b[^>]*>", re.IGNORECASE)
_TABLE_CLOSE_RE = re.compile(r"</table\s*>", re.IGNORECASE)
_COMMENT_RE = re.compile(r"<!--.*?-->")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_RE = re.compile(r"^(\s*)([-+*]|(?:\d+\.)+\d*|\d+\))\s+(.+)$")
_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]+\)")
_BOLD_RE = re.compile(r"(\*\*|__)(.+?)\1")
_ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_ITALIC_UNDERSCORE_RE = re.compile(r"(?<!\w)_([^_\n]+)_(?!\w)")
_CODE_RE = re.compile(r"`([^`\n]+)`")


class HtmlTableCell(BaseModel):
    """One origin cell in an HTML table (covered cells are absent)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str
    rowspan: int = Field(default=1, ge=1)
    colspan: int = Field(default=1, ge=1)


class HtmlTable(BaseModel):
    """A strict HTML table block in hybrid benchmark Markdown."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_line: int = Field(ge=0)
    end_line: int = Field(ge=1)
    rows: list[list[HtmlTableCell]]

    @property
    def data_row_count(self) -> int:
        """All rows are data rows (contract: no thead / header signal)."""
        return len(self.rows)


def normalize_unicode(text: str) -> str:
    """Apply the benchmark's Unicode normalization without changing case."""
    if not isinstance(text, str):
        raise TypeError("Markdown must be a string")
    return unicodedata.normalize("NFKC", text).replace("ё", "е").replace("Ё", "Е")


def normalize_inline_text(text: str) -> str:
    """Keep visible inline text while removing Markdown presentation wrappers."""
    value = normalize_unicode(text)
    value = _LINK_RE.sub(r"\1", value)
    value = _CODE_RE.sub(r"\1", value)
    value = _BOLD_RE.sub(r"\2", value)
    value = _ITALIC_STAR_RE.sub(r"\1", value)
    value = _ITALIC_UNDERSCORE_RE.sub(r"\1", value)
    value = _COMMENT_RE.sub("", value)
    value = re.sub(r"\\([\\`*_{}\[\]()#+.!|>-])", r"\1", value)
    return " ".join(value.split())


def normalize_cell_text(text: str) -> str:
    """Collapse whitespace; strip presentation noise inside table cells."""
    value = normalize_unicode(text)
    value = _BR_RE.sub(" ", value)
    value = _COMMENT_RE.sub("", value)
    return " ".join(value.split())


def find_html_table_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` character spans for top-level ``<table>`` blocks."""
    spans: list[tuple[int, int]] = []
    position = 0
    while True:
        open_match = _TABLE_OPEN_RE.search(text, position)
        if open_match is None:
            break
        close_match = _TABLE_CLOSE_RE.search(text, open_match.end())
        if close_match is None:
            raise ValueError("Unclosed HTML table")
        inner = text[open_match.end() : close_match.start()]
        if _TABLE_OPEN_RE.search(inner):
            raise ValueError("Nested HTML tables are not supported")
        spans.append((open_match.start(), close_match.end()))
        position = close_match.end()
    return spans


def _offset_to_line(offset: int, text: str) -> int:
    return text.count("\n", 0, offset)


class _HtmlTableParser(HTMLParser):
    """Parse one ``<table>…</table>`` fragment into origin cells."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[HtmlTableCell]] = []
        self._row: list[HtmlTableCell] | None = None
        self._cell_chunks: list[str] | None = None
        self._rowspan = 1
        self._colspan = 1
        self._table_depth = 0
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        attr_map = {key.lower(): (value or "") for key, value in attrs}
        if name == "table":
            self._table_depth += 1
            if self._table_depth > 1:
                raise ValueError("Nested HTML tables are not supported")
            return
        if name in ("thead", "tbody", "tfoot", "colgroup", "col"):
            return
        if name == "tr":
            if self._row is not None:
                raise ValueError("Malformed HTML table: nested <tr>")
            self._row = []
            return
        if name in ("td", "th"):
            if self._row is None:
                raise ValueError("Malformed HTML table: cell outside <tr>")
            if self._in_cell:
                raise ValueError("Malformed HTML table: nested cell")
            self._in_cell = True
            self._cell_chunks = []
            self._rowspan = _parse_span_attr(attr_map.get("rowspan", "1"), "rowspan")
            self._colspan = _parse_span_attr(attr_map.get("colspan", "1"), "colspan")
            return
        if name == "br" and self._in_cell:
            assert self._cell_chunks is not None
            self._cell_chunks.append(" ")
            return
        if name == "caption":
            raise ValueError("Malformed HTML table: <caption> is not supported")

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name == "table":
            self._table_depth -= 1
            return
        if name == "tr":
            if self._row is None:
                raise ValueError("Malformed HTML table: stray </tr>")
            self.rows.append(self._row)
            self._row = None
            return
        if name in ("td", "th"):
            if not self._in_cell or self._row is None or self._cell_chunks is None:
                raise ValueError("Malformed HTML table: stray cell end tag")
            text = normalize_cell_text("".join(self._cell_chunks))
            self._row.append(
                HtmlTableCell(text=text, rowspan=self._rowspan, colspan=self._colspan)
            )
            self._in_cell = False
            self._cell_chunks = None
            self._rowspan = 1
            self._colspan = 1

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            assert self._cell_chunks is not None
            self._cell_chunks.append(data)

    def close(self) -> None:
        super().close()
        if self._table_depth != 0 or self._row is not None or self._in_cell:
            raise ValueError("Malformed HTML table: unclosed tags")


def _parse_span_attr(raw: str, name: str) -> int:
    value = raw.strip() or "1"
    if not value.isdigit():
        raise ValueError(f"invalid cell {name}: {raw!r}")
    number = int(value)
    if number < 1:
        raise ValueError(f"invalid cell {name}: {raw!r}")
    return number


def _validate_span_grid(rows: list[list[HtmlTableCell]]) -> None:
    if not rows:
        raise ValueError("HTML table has no rows")
    occupied: set[tuple[int, int]] = set()
    max_col = 0
    for row_index, row in enumerate(rows):
        if not row:
            raise ValueError(f"HTML table has an empty row at index {row_index}")
        column = 0
        for cell in row:
            while (row_index, column) in occupied:
                column += 1
            for row_delta in range(cell.rowspan):
                for col_delta in range(cell.colspan):
                    key = (row_index + row_delta, column + col_delta)
                    if key in occupied:
                        raise ValueError(
                            f"HTML table has overlapping spans at row={key[0]} col={key[1]}"
                        )
                    occupied.add(key)
            column += cell.colspan
            max_col = max(max_col, column)
    expected_rows = max(row for row, _ in occupied) + 1
    if expected_rows != len(rows):
        raise ValueError(
            f"HTML table rowspan extends past declared rows: need {expected_rows}, got {len(rows)}"
        )
    for row_index in range(len(rows)):
        covered = {col for row, col in occupied if row == row_index}
        if covered != set(range(max_col)):
            raise ValueError(
                f"HTML table has a ragged or gapped grid at row {row_index}: "
                f"expected columns 0..{max_col - 1}, got {sorted(covered)}"
            )


def parse_html_table_fragment(fragment: str) -> list[list[HtmlTableCell]]:
    """Parse a single ``<table>…</table>`` string into origin-cell rows."""
    parser = _HtmlTableParser()
    try:
        parser.feed(fragment)
        parser.close()
    except AssertionError as exc:
        raise ValueError("Malformed HTML table") from exc
    _validate_span_grid(parser.rows)
    return parser.rows


def _span_line_range(start: int, end: int, text: str) -> tuple[int, int]:
    """Return inclusive-exclusive line indices covering ``text[start:end]``."""
    start_line = _offset_to_line(start, text)
    last_content = end - 1 if end > start else start
    end_line = _offset_to_line(last_content, text) + 1
    return start_line, end_line


def parse_html_tables(markdown: str) -> list[HtmlTable]:
    """Parse all HTML tables from hybrid Markdown (prose + ``<table>`` blocks)."""
    source = normalize_unicode(markdown).replace("\r\n", "\n").replace("\r", "\n")
    tables: list[HtmlTable] = []
    for start, end in find_html_table_spans(source):
        start_line, end_line = _span_line_range(start, end, source)
        tables.append(
            HtmlTable(
                start_line=start_line,
                end_line=end_line,
                rows=parse_html_table_fragment(source[start:end]),
            )
        )
    return tables


def render_html_table(table: HtmlTable) -> str:
    """Render a parsed table as deterministic contract HTML (all ``<td>``)."""
    row_parts: list[str] = []
    for row in table.rows:
        cell_parts: list[str] = []
        for cell in row:
            attrs: list[str] = []
            if cell.rowspan != 1:
                attrs.append(f'rowspan="{cell.rowspan}"')
            if cell.colspan != 1:
                attrs.append(f'colspan="{cell.colspan}"')
            attr_str = (" " + " ".join(attrs)) if attrs else ""
            cell_parts.append(
                f"<td{attr_str}>{html.escape(cell.text, quote=False)}</td>"
            )
        row_parts.append("<tr>" + "".join(cell_parts) + "</tr>")
    return "<table>" + "".join(row_parts) + "</table>"


def _normalize_non_table_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    heading = _HEADING_RE.fullmatch(stripped)
    if heading:
        return f"{heading.group(1)} {normalize_inline_text(heading.group(2))}"
    list_item = _LIST_RE.fullmatch(line)
    if list_item:
        indent, marker, body = list_item.groups()
        return f"{indent}{marker} {normalize_inline_text(body)}"
    return normalize_inline_text(_BR_RE.sub(" ", stripped))


def _canonicalize_prose(prose: str) -> str:
    return "\n".join(_normalize_non_table_line(line) for line in prose.split("\n"))


def _compact_blank_lines(text: str) -> str:
    compact: list[str] = []
    for line in text.split("\n"):
        if line or (compact and compact[-1]):
            compact.append(line)
    while compact and not compact[-1]:
        compact.pop()
    return "\n".join(compact)


def canonicalize_ground_truth(markdown: str) -> str:
    """Canonicalize hybrid Markdown: prose + deterministic HTML tables."""
    source = normalize_unicode(markdown).replace("\r\n", "\n").replace("\r", "\n")
    source = _ATTACHMENT_RE.sub("", source)
    if _UNRESOLVED_TABLE_RE.search(source):
        raise ValueError("Unresolved table placeholder in benchmark Markdown")

    spans = find_html_table_spans(source)
    if not spans:
        return _compact_blank_lines(_canonicalize_prose(source))

    chunks: list[str] = []
    cursor = 0
    for start, end in spans:
        prose = source[cursor:start]
        if prose:
            chunks.append(_canonicalize_prose(prose))
        rows = parse_html_table_fragment(source[start:end])
        table = HtmlTable(start_line=0, end_line=1, rows=rows)
        # Always emit tables as their own block lines in canonical form.
        if chunks and not chunks[-1].endswith("\n") and chunks[-1] != "":
            chunks.append("\n")
        chunks.append(render_html_table(table))
        chunks.append("\n")
        cursor = end
    trailing = source[cursor:]
    if trailing:
        chunks.append(_canonicalize_prose(trailing))
    return _compact_blank_lines("".join(chunks))


def canonicalize_pair(pred_markdown: str, gt_markdown: str) -> tuple[str, str]:
    """Canonicalize prediction and GT under the same HTML-table contract."""
    return canonicalize_ground_truth(pred_markdown), canonicalize_ground_truth(gt_markdown)


def _plain_from_canonical(markdown: str) -> str:
    lines = markdown.splitlines()
    tables = parse_html_tables(markdown)
    table_by_start = {table.start_line: table for table in tables}
    chunks: list[str] = []
    line_index = 0
    while line_index < len(lines):
        table = table_by_start.get(line_index)
        if table is not None:
            for row in table.rows:
                for cell in row:
                    visible = normalize_inline_text(cell.text)
                    if visible:
                        chunks.append(visible)
            line_index = table.end_line
            continue

        line = lines[line_index].strip()
        line_index += 1
        if not line:
            continue
        heading = _HEADING_RE.fullmatch(line)
        if heading:
            line = heading.group(2)
        else:
            list_item = _LIST_RE.fullmatch(line)
            if list_item:
                line = list_item.group(3)
            line = re.sub(r"^>\s*", "", line)
        visible = normalize_inline_text(_BR_RE.sub(" ", line))
        if visible:
            chunks.append(visible)
    return " ".join(chunks)


def markdown_to_plain_text(markdown: str) -> str:
    """Convert canonicalizable Markdown to normalized visible reading-order text."""
    return _plain_from_canonical(canonicalize_ground_truth(markdown))
