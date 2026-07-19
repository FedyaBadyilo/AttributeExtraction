"""
Walk content.structure and build FormattedNode tree. No access to content.tables.
"""

from dedoc.api.schema.tree_node import TreeNode

from research.steps.markdown_formatting.domain.models import FormattedNode, FormattedNodeMetadata
from research.steps.markdown_formatting.domain.structure.header_levels import (
    HEADER_LEVEL_MAPPING,
    LIST_LEVEL_MAPPING,
    get_level_1,
)
from research.steps.markdown_formatting.domain.structure.node_formatter import format_node


def process_structure(structure: TreeNode) -> FormattedNode:
    """Process content.structure only (metadata + annotations). No access to content.tables."""
    return _format_structure_node(structure)


def _format_structure_node(node: TreeNode) -> FormattedNode:
    """Format one node and recurse into subparagraphs."""
    text, metadata_contributions = format_node(node)

    paragraph_type = node.metadata.paragraph_type
    page_id = node.metadata.page_id

    level_1 = get_level_1(paragraph_type)
    level_2 = HEADER_LEVEL_MAPPING.get(paragraph_type) or LIST_LEVEL_MAPPING.get(paragraph_type) if paragraph_type else None

    metadata_out = FormattedNodeMetadata(
        page_id=page_id,
        paragraph_type=paragraph_type,
        level_1=level_1,
        level_2=level_2,
        **metadata_contributions,
    )

    sub_nodes = [_format_structure_node(sub) for sub in node.subparagraphs]

    return FormattedNode(
        node_id=node.node_id,
        text=text,
        metadata=metadata_out,
        subparagraphs=sub_nodes,
    )
