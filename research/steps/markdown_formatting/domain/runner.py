"""Dedoc DocumentContent → FormattedDocument conversion.

Structure and tables are processed independently:
- structure: tree walk, node metadata, annotation processors;
- tables: HTML → markdown conversion from ``content.tables``.
"""

from dedoc.api.schema.document_content import DocumentContent

from research.steps.markdown_formatting.domain.models import FormattedDocument
from research.steps.markdown_formatting.domain.structure.walk import process_structure
from research.steps.markdown_formatting.domain.tables.table_processing import process_tables


def format_document(content: DocumentContent) -> FormattedDocument:
    """Build formatted markdown output from dedoc ``DocumentContent``."""
    structure = process_structure(content.structure)
    tables_out = process_tables(content)
    return FormattedDocument(structure=structure, tables=tables_out)
