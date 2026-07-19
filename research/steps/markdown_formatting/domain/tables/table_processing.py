"""
Processing of content.tables: convert to HTML and to list of FormattedTable.
Not used during structure walk. Independent from structure package.
"""

from dedoc.api.schema.document_content import DocumentContent
from dedoc.api.schema.table import Table

from research.steps.markdown_formatting.domain.models import FormattedTable
from research.steps.markdown_formatting.domain.tables.table_to_html import (
    dedoc_table_to_html,
)


def build_table_html_map(tables: list[Table]) -> dict[str, str]:
    """From content.tables build {table_uid: html_string}."""
    if not tables:
        return {}

    return {
        api_table.metadata.uid: dedoc_table_to_html(api_table)
        for api_table in tables
    }


def process_tables(content: DocumentContent) -> list[FormattedTable]:
    """Build list of FormattedTable from content.tables (uid + html)."""
    table_html_by_uid = build_table_html_map(content.tables)
    return [FormattedTable(uid=uid, html=html) for uid, html in table_html_by_uid.items()]
