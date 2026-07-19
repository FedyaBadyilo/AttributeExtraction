"""
Node-level formatting: layer 1 = annotations (segments), layer 2 = structural (headers, lists).
Builds formatted markdown text from segments; for header nodes produces "# title" line.
Returns (formatted_text, metadata_contributions dict merged into node metadata at top level).
"""

from dedoc.api.schema.tree_node import TreeNode

from research.steps.markdown_formatting.domain.structure.annotations.pipeline import process_annotations
from research.steps.markdown_formatting.domain.structure.annotations.processors.bold.processor import BOLD_WRAPPER
from research.steps.markdown_formatting.domain.structure.annotations.segments import Segment
from research.steps.markdown_formatting.domain.structure.header_levels import HEADER_LEVEL_MAPPING, is_header_type

HEADER_PREFIX_CHAR = "#"


def _normalize_header_text(text: str) -> str:
    return text.strip()


def _header_markdown_line(level_2: int, header_title: str) -> str:
    """Produce markdown line for a header (e.g. '## Title\\n')."""
    prefix = HEADER_PREFIX_CHAR * level_2 + " "
    return prefix + header_title.strip() + "\n"


def _segments_to_text(segments: list[Segment]) -> str:
    """Build plain text from segments in document order (no structural formatting)."""
    sorted_segments = sorted(segments, key=lambda seg: (seg.start, seg.end))
    return "".join(seg.content for seg in sorted_segments)


def _detect_bold(segments: list[Segment], header_span_end: int) -> bool:
    """Check if any segment covering the header span contains bold markers (**...**)."""
    for seg in segments:
        if seg.start == seg.end:
            continue
        if seg.start < header_span_end and seg.content.startswith(BOLD_WRAPPER):
            return True
    return False


def _strip_bold_wrapper(text: str) -> str:
    """Remove outermost ** wrapper if present: '**x**' → 'x'."""
    if text.startswith(BOLD_WRAPPER) and text.endswith(BOLD_WRAPPER) and len(text) > len(BOLD_WRAPPER) * 2:
        return text[len(BOLD_WRAPPER) : -len(BOLD_WRAPPER)]
    return text


def _format_header_node(
    level_2: int,
    original_text: str,
    segments: list[Segment],
) -> str:
    """
    Build formatted markdown for a header node from segments. Content in [0, header_span_end)
    is replaced by a single "# **title**\n" line (with bold if source was bold); rest is output as-is.
    """
    header_title = original_text[: original_text.find("\n")].strip() if "\n" in original_text else original_text.strip()
    if not header_title:
        header_title = _normalize_header_text(original_text)
    idx = original_text.find("\n")
    header_span_end = len(original_text) if idx < 0 else idx
    if header_span_end == 0:
        return _header_markdown_line(level_2, header_title)

    sorted_segments = sorted(segments, key=lambda seg: (seg.start, seg.end))
    is_bold = _detect_bold(sorted_segments, header_span_end)

    prefix = HEADER_PREFIX_CHAR * level_2 + " "
    title = header_title.strip()
    header_line_str = prefix + (BOLD_WRAPPER + title + BOLD_WRAPPER if is_bold else title) + "\n"

    header_inserted = False
    parts: list[str] = []
    for seg in sorted_segments:
        if seg.start == seg.end:
            parts.append(seg.content)
            continue
        if seg.end <= header_span_end:
            if not header_inserted:
                parts.append(header_line_str)
                header_inserted = True
            continue
        if seg.start >= header_span_end:
            if not header_inserted:
                parts.append(header_line_str)
                header_inserted = True
            parts.append(seg.content)
            continue
        # Spanning segment: content may be a replacement (e.g. bold "**" + span + "**")
        # so its length differs from (seg.end - seg.start).
        local_cut = header_span_end - seg.start
        orig_span_len = seg.end - seg.start
        content_cut = local_cut
        if len(seg.content) != orig_span_len:
            prefix_estimate = (len(seg.content) - orig_span_len) // 2
            content_cut = local_cut + prefix_estimate
        if not header_inserted:
            parts.append(header_line_str)
            header_inserted = True
        tail = seg.content[content_cut:]
        if is_bold and tail.endswith(BOLD_WRAPPER):
            tail = tail[: -len(BOLD_WRAPPER)]
            leading, _, rest = tail.partition("\n")
            if rest:
                tail = leading + "\n" + BOLD_WRAPPER + rest + BOLD_WRAPPER
            elif tail.strip():
                tail = BOLD_WRAPPER + tail + BOLD_WRAPPER
        parts.append(tail)
    result = "".join(parts)
    if not result.strip() and header_title:
        return header_line_str
    return result


def format_node(node: TreeNode) -> tuple[str, dict]:
    """
    Layer 1: run annotation pipeline (returns segments). Layer 2: apply structural
    formatting from paragraph_type. Returns (formatted markdown text, metadata_contributions).
    """
    paragraph_type = node.metadata.paragraph_type
    original_text = node.text

    segments, metadata_contributions = process_annotations(node)

    if is_header_type(paragraph_type):
        level_2 = HEADER_LEVEL_MAPPING[paragraph_type]
        formatted = _format_header_node(level_2, original_text, segments)
        return formatted, metadata_contributions

    text = _segments_to_text(segments)
    return text, metadata_contributions
