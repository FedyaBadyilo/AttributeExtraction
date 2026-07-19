"""
Shared utilities for annotation processing. Filter node annotations by dedoc annotation class.
Uses dedoc TreeNode and api.schema Annotation for typing.
"""

from typing import Type

from dedoc.api.schema.annotation import Annotation
from dedoc.api.schema.tree_node import TreeNode


def extract_annotations_by_type(
    node: TreeNode,
    annotation_class: Type[Annotation],
) -> list[Annotation]:
    """
    Return annotations from node whose name matches the dedoc annotation class.
    Uses annotation_class.name so we stay aligned with the library.
    """
    name = annotation_class.name
    return [ann for ann in (node.annotations or []) if ann.name == name]
