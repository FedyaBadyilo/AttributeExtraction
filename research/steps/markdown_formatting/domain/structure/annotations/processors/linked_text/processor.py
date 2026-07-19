"""LinkedText annotation processor (replace): append linked content inline as "span_content [value]"."""

from dedoc.api.schema.annotation import Annotation

from research.steps.markdown_formatting.domain.structure.annotations.processors.base import ProcessorResult

LINKED_OPEN = " ["
LINKED_CLOSE = "]"


def linked_text_processor(
    annotation: Annotation,
    span_content: str,
) -> ProcessorResult:
    """Replace span with "span_content [linked_value]". If value is empty, leave span unchanged."""
    linked_value = (annotation.value or "").strip()
    if not linked_value:
        return span_content, None
    return f"{span_content}{LINKED_OPEN}{linked_value}{LINKED_CLOSE}", None
