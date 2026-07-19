"""Output models for markdown_formatting step.

Serialization to JSON via ``model_dump()``.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class FormattedNodeMetadata(BaseModel):
    """Simplified node metadata in formatted output.

    Base fields are always set; processor metadata_contributions (e.g. tables)
    are merged at the same level via ``extra``.
    """

    model_config = ConfigDict(extra="allow")

    page_id: int = Field(description="Page number where paragraph starts")
    paragraph_type: str = Field(default="", description="Type of the document line/paragraph")
    level_1: int | None = Field(default=None, description="1=header, 2=list, None=body")
    level_2: int | None = Field(default=None, description="Header/list sub-level from patterns")


class FormattedNode(BaseModel):
    """Single node in the formatted structure tree."""

    node_id: str = Field(description="Document element identifier")
    text: str = Field(description="Markdown text of the node")
    metadata: FormattedNodeMetadata = Field(description="Simplified metadata")
    subparagraphs: List["FormattedNode"] = Field(default_factory=list, description="Children nodes")


FormattedNode.model_rebuild()


class FormattedTable(BaseModel):
    """Single table in formatted output."""

    uid: str = Field(description="Table identifier")
    html: str = Field(default="", description="HTML representation of the table")


class FormattedDocument(BaseModel):
    """Root output of ``format_document``."""

    structure: FormattedNode = Field(description="Root of the formatted tree")
    tables: List[FormattedTable] = Field(default_factory=list, description="List of tables (uid, html)")
