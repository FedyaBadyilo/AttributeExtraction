"""Current dedoc-only parsing pipeline and benchmark Markdown renderer."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from research.steps.markdown_formatting.domain.models import (
    FormattedDocument,
    FormattedNode,
)
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
)

_TABLE_PLACEHOLDER_RE = re.compile(
    re.escape(TABLE_PLACEHOLDER_TEMPLATE).replace(re.escape("{}"), r'([^"]+)')
)
_ATTACHMENT_PLACEHOLDER_RE = re.compile(r"<attachment [^<>\r\n]*>")


def _flatten_dfs(node: FormattedNode) -> str:
    return node.text + "".join(_flatten_dfs(child) for child in node.subparagraphs)


def render_formatted_document(document: FormattedDocument) -> str:
    """Flatten the tree in DFS order and resolve dedoc sidecar placeholders."""
    tables_by_id: dict[str, str] = {}
    for table in document.tables:
        if table.uid in tables_by_id:
            raise ValueError(f"duplicate sidecar table ID: {table.uid}")
        tables_by_id[table.uid] = table.html

    flattened = _flatten_dfs(document.structure)
    used_table_ids: set[str] = set()

    def replace_table(match: re.Match[str]) -> str:
        table_id = match.group(1)
        if table_id not in tables_by_id:
            raise ValueError(f"unresolved table ID: {table_id}")
        if table_id in used_table_ids:
            raise ValueError(f"duplicate table placeholder ID: {table_id}")
        used_table_ids.add(table_id)
        return tables_by_id[table_id]

    rendered = _TABLE_PLACEHOLDER_RE.sub(replace_table, flattened)
    if "<table_ref " in rendered:
        raise ValueError("unresolved malformed table placeholder")

    orphan_table_ids = sorted(set(tables_by_id) - used_table_ids)
    if orphan_table_ids:
        raise ValueError(f"orphan sidecar table IDs: {', '.join(orphan_table_ids)}")

    return _ATTACHMENT_PLACEHOLDER_RE.sub("", rendered)

def run_dedoc_pipeline(
    input_path: Path,
    work_dir: Path,
    *,
    config: dict[str, Any],
    converter: Callable[..., Any] | None = None,
    formatter: Callable[[Any], FormattedDocument] | None = None,
) -> tuple[Any, FormattedDocument, str]:
    """Run convert_document → format_document → strict DFS rendering."""
    work_dir.mkdir(parents=True, exist_ok=True)
    if converter is None:
        from research.steps.ocr.domain import convert_document

        converter = convert_document
    if formatter is None:
        from research.steps.markdown_formatting.domain import format_document

        formatter = format_document

    parsed = converter(file_path=input_path, output_dir=work_dir, config=config)
    formatted = formatter(parsed.content)
    prediction = render_formatted_document(formatted)
    return parsed, formatted, prediction


__all__ = ["render_formatted_document", "run_dedoc_pipeline"]
