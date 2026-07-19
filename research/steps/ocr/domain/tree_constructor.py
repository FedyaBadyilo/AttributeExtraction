"""Custom TreeConstructor for dedoc.

Fixes two issues in the default implementation:
1. Annotation offsets are shifted correctly when multiline lines are merged,
   preserving concrete TableAnnotation / AttachAnnotation types and their
   ``is_mergeable`` flag.
2. Multiline merge is blocked for a node when a table or attachment anchor
   appears after the first visible character of the node's text (i.e. the
   node is a table caption, not free-running text).
"""
from typing import List, Optional

from dedoc.data_structures.annotation import Annotation
from dedoc.data_structures.concrete_annotations.attach_annotation import AttachAnnotation
from dedoc.data_structures.concrete_annotations.table_annotation import TableAnnotation
from dedoc.data_structures.line_with_meta import LineWithMeta
from dedoc.data_structures.parsed_document import ParsedDocument
from dedoc.data_structures.tree_node import TreeNode
from dedoc.data_structures.unstructured_document import UnstructuredDocument
from dedoc.structure_constructors.concrete_structure_constructors.tree_constructor import (
    TreeConstructor,
)


def _annotation_is_table_or_attach(ann) -> bool:
    return isinstance(ann, (TableAnnotation, AttachAnnotation))


def _first_visible_char_index(line: str) -> int:
    return len(line) - len(line.lstrip())


def _table_or_attach_after_visible_text(line: str | None, ann) -> bool:
    """Return True when a table/attach annotation starts after the first visible char."""
    if not _annotation_is_table_or_attach(ann):
        return False
    t0 = _first_visible_char_index(line or "")
    return ann.start > t0


def line_has_table_or_attach_after_visible_text(
    line: str | None, annotations: list
) -> bool:
    """True if any table/attachment anchor lies after the first non-whitespace character."""
    return any(_table_or_attach_after_visible_text(line, a) for a in annotations)


def _shift_annotations_preserve_mergeable(
    line: LineWithMeta, text_length: int
) -> List[Annotation]:
    """Like TreeNode.__shift_annotations, but keeps concrete types and is_mergeable."""
    out: List[Annotation] = []
    for a in line.annotations:
        s = a.start + text_length
        e = a.end + text_length
        mergeable = getattr(a, "is_mergeable", True)
        if isinstance(a, TableAnnotation):
            shifted: Annotation = TableAnnotation(value=a.value, start=s, end=e)
        elif isinstance(a, AttachAnnotation):
            shifted = AttachAnnotation(attach_uid=a.value, start=s, end=e)
        else:
            shifted = Annotation(
                start=s, end=e, name=a.name, value=a.value, is_mergeable=mergeable
            )
        shifted.is_mergeable = mergeable
        out.append(shifted)
    return out


def _node_blocks_multiline_merge(node: TreeNode) -> bool:
    """Return True when the node should not absorb the next line via add_text."""
    return line_has_table_or_attach_after_visible_text(node.text, node.annotations)


class CustomTreeConstructor(TreeConstructor):
    """TreeConstructor with mergeable-preserving annotation shifts and table-aware multiline blocking."""

    def construct(
        self, document: UnstructuredDocument, parameters: Optional[dict] = None
    ) -> ParsedDocument:
        from dedoc.data_structures.document_content import DocumentContent
        from dedoc.data_structures.document_metadata import DocumentMetadata

        # Patch the private shift method for this call only.
        TreeNode._TreeNode__shift_annotations = staticmethod(  # type: ignore[attr-defined]
            _shift_annotations_preserve_mergeable
        )

        document_name, not_document_name = self._TreeConstructor__get_document_name(  # type: ignore[attr-defined]
            document.lines
        )
        not_document_name = self._TreeConstructor__add_lists(not_document_name)  # type: ignore[attr-defined]
        tree = TreeNode.create(lines=document_name)

        for line in not_document_name:
            hl_equal = line.metadata.hierarchy_level == tree.metadata.hierarchy_level
            type_equal = (
                line.metadata.hierarchy_level.line_type
                == tree.metadata.hierarchy_level.line_type
            )
            if (
                line.metadata.hierarchy_level.can_be_multiline
                and hl_equal
                and type_equal
                and not _node_blocks_multiline_merge(tree)
            ):
                tree.add_text(line)
            else:
                while tree.metadata.hierarchy_level >= line.metadata.hierarchy_level:
                    tree = tree.parent
                tree = tree.add_child(line=line)

        tree = tree.get_root()
        tree.merge_annotations()
        document_content = DocumentContent(tables=document.tables, structure=tree)
        metadata = DocumentMetadata(**document.metadata)
        return ParsedDocument(
            content=document_content, metadata=metadata, warnings=document.warnings
        )
