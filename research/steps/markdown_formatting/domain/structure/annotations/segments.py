"""
Segment model for annotation pipeline: (start, end, content) in original text coordinates.
Supports replace_span (overwrite range) and insert_at (zero-length segment at position).
"""

from typing import NamedTuple


class Segment(NamedTuple):
    """start==end for insertions (zero-length placeholder)."""

    start: int
    end: int
    content: str


def get_content(segments: list[Segment], s: int, e: int) -> str:
    """
    Concatenate content of all segments that overlap [s, e), in order by start.
    Segments with start == end (insertions) do not participate in the range.
    Overlapping parts are clipped to [s, e).
    """
    parts: list[str] = []
    for seg in segments:
        if seg.start == seg.end:
            continue
        if seg.end <= s or seg.start >= e:
            continue
        clip_start = max(seg.start, s)
        clip_end = min(seg.end, e)
        if clip_start >= clip_end:
            continue
        local_start = clip_start - seg.start
        local_end = clip_end - seg.start
        parts.append(seg.content[local_start:local_end])
    return "".join(parts)


def replace_span(segments: list[Segment], s: int, e: int, new_content: str) -> None:
    """
    Remove or trim all segments overlapping [s, e), then insert (s, e, new_content).
    Mutates segments in place; keeps list sorted by (start, end).
    """
    new_list: list[Segment] = []
    for seg in segments:
        if seg.start == seg.end:
            if seg.start < s or seg.start > e:
                new_list.append(seg)
            continue
        if seg.end <= s or seg.start >= e:
            new_list.append(seg)
            continue
        if seg.start < s:
            new_list.append(Segment(seg.start, s, seg.content[: s - seg.start]))
        if seg.end > e:
            new_list.append(Segment(e, seg.end, seg.content[e - seg.start :]))
    new_list.append(Segment(s, e, new_content))
    new_list.sort(key=lambda seg: (seg.start, seg.end))
    segments.clear()
    segments.extend(new_list)


def insert_at(segments: list[Segment], pos: int, content: str) -> None:
    """
    Insert content at position pos: split the segment that contains pos so the
    insertion appears in document order. Mutates segments in place.
    """
    new_list: list[Segment] = []
    found = False
    for i, seg in enumerate(segments):
        if seg.start == seg.end:
            new_list.append(seg)
            continue
        if pos < seg.start or pos > seg.end:
            new_list.append(seg)
            continue
        if pos > seg.start:
            new_list.append(Segment(seg.start, pos, seg.content[: pos - seg.start]))
        new_list.append(Segment(pos, pos, content))
        if pos < seg.end:
            new_list.append(Segment(pos, seg.end, seg.content[pos - seg.start :]))
        found = True
        remaining = segments[i + 1 :]
        if remaining:
            new_list.extend(remaining)
        break
    if not found:
        new_list.append(Segment(pos, pos, content))
    new_list.sort(key=lambda seg: (seg.start, seg.end))
    segments.clear()
    segments.extend(new_list)


def build_output(segments: list[Segment]) -> str:
    """
    Produce final string from segments in document order. Sort by (start, end) so
    insertions (s, s) come before (s, e). Concatenate content only (no structural formatting).
    """
    sorted_segments = sorted(segments, key=lambda seg: (seg.start, seg.end))
    return "".join(seg.content for seg in sorted_segments)
