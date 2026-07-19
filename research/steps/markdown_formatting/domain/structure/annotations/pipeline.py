"""
Single entry point for processing node annotations: segment-based, two phases.
Returns (segments, merged_metadata_contributions). Formatter builds final text from segments.
Processors and inject/replace split come from PROCESSOR_REGISTRY.
"""

from typing import Any

from dedoc.api.schema.annotation import Annotation
from dedoc.api.schema.tree_node import TreeNode

from research.steps.markdown_formatting.domain.structure.annotations.processors.registry import PROCESSOR_REGISTRY
from research.steps.markdown_formatting.domain.structure.annotations.segments import Segment, get_content, insert_at, replace_span

# Derived from registry: types we process, type -> processor, and inject-only types
_PROCESSED_NAMES = {entry[0].name for entry in PROCESSOR_REGISTRY}
_PROCESSOR_BY_NAME = {entry[0].name: entry[1] for entry in PROCESSOR_REGISTRY}
_INJECT_NAMES = {entry[0].name for entry in PROCESSOR_REGISTRY if entry[2]}


def get_processor_for_annotation(annotation: Annotation) -> Any | None:
    """Return the processor callable for this annotation, or None if not processed."""
    return _PROCESSOR_BY_NAME.get(annotation.name)


def _is_inject_annotation(annotation: Annotation) -> bool:
    return annotation.name in _INJECT_NAMES


def _merge_metadata_contributions(list_of_dicts: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge processor metadata_contributions: same key with list values are concatenated; others last-wins."""
    result: dict[str, Any] = {}
    for d in list_of_dicts:
        for k, v in d.items():
            if k in result and isinstance(result[k], list) and isinstance(v, list):
                result[k].extend(v)
            else:
                result[k] = v.copy() if isinstance(v, list) else v
    return result


def process_annotations(node: TreeNode) -> tuple[list[Segment], dict[str, Any]]:
    """
    Process annotations in two phases: replace (bold, etc.) first, then inject (table).
    Returns (segments, merged_metadata_contributions).
    """
    original_text = node.text
    annotations = node.annotations
    segments = [Segment(0, len(original_text), original_text)]
    relevant = [ann for ann in annotations if ann.name in _PROCESSED_NAMES]
    if not relevant:
        return segments, {}

    text_len = len(original_text)
    metadata_contributions_list: list[dict[str, Any]] = []

    replace_anns = [a for a in relevant if not _is_inject_annotation(a)]
    inject_anns = [a for a in relevant if _is_inject_annotation(a)]

    replace_anns.sort(key=lambda a: (a.start, a.end))
    for ann in replace_anns:
        processor = get_processor_for_annotation(ann)
        if processor is None:
            continue
        start = ann.start
        end = min(ann.end, text_len)
        span_content = get_content(segments, start, end)
        replacement, metadata_contribution = processor(ann, span_content)
        replace_span(segments, start, end, replacement)
        if metadata_contribution:
            metadata_contributions_list.append(metadata_contribution)

    inject_anns.sort(key=lambda a: (a.start, a.end))
    for ann in inject_anns:
        processor = get_processor_for_annotation(ann)
        if processor is None:
            continue
        start = ann.start
        end = min(ann.end, text_len)
        span_content = get_content(segments, start, end)
        replacement, metadata_contribution = processor(ann, span_content)
        insert_at(segments, start, replacement)
        if metadata_contribution:
            metadata_contributions_list.append(metadata_contribution)

    return segments, _merge_metadata_contributions(metadata_contributions_list)
