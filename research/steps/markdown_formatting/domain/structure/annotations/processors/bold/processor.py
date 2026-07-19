"""Bold annotation processor (replace): wrap span_content in markdown **."""

from dedoc.api.schema.annotation import Annotation

from research.steps.markdown_formatting.domain.structure.annotations.processors.base import ProcessorResult

BOLD_WRAPPER = "**"


def bold_processor(
    annotation: Annotation,
    span_content: str,
) -> ProcessorResult:
    """Wrap span content in ** for markdown bold. No metadata."""
    if annotation.value == "True" and span_content:
        replacement = f"{BOLD_WRAPPER}{span_content}{BOLD_WRAPPER}"
    else:
        replacement = span_content
    return replacement, None
