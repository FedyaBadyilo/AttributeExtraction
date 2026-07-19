"""Minimal LineWithMeta factory helpers for offline tests.

These helpers build dedoc data structures without requiring a real PDF or a
running dedoc service.
"""
from dedoc.data_structures import BoldAnnotation, HierarchyLevel, LineWithMeta
from dedoc.data_structures.line_metadata import LineMetadata


def make_hierarchy_level(
    line_type: str = "raw_text",
    level_1: int = 0,
    level_2: int = 0,
    can_be_multiline: bool = False,
) -> HierarchyLevel:
    return HierarchyLevel(
        line_type=line_type,
        level_1=level_1,
        level_2=level_2,
        can_be_multiline=can_be_multiline,
    )


def make_line(
    text: str,
    *,
    line_type: str = "raw_text",
    level_1: int = 0,
    level_2: int = 0,
    can_be_multiline: bool = False,
    bold: bool = False,
    uid: str = "line_uid",
) -> LineWithMeta:
    hl = make_hierarchy_level(line_type, level_1, level_2, can_be_multiline)
    metadata = LineMetadata(
        tag_hierarchy_level=hl,
        hierarchy_level=hl,
        page_id=1,
        line_id=1,
    )
    annotations = []
    if bold and text:
        annotations.append(BoldAnnotation(start=0, end=len(text), value="True"))
    return LineWithMeta(line=text, metadata=metadata, annotations=annotations, uid=uid)
