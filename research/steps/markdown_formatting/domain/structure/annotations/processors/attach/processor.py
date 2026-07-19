"""Attachment annotation processor (inject): insert placeholder at span start."""

from dedoc.api.schema.annotation import Annotation

from research.steps.markdown_formatting.domain.structure.annotations.processors.base import ProcessorResult

ATTACH_PLACEHOLDER_TEMPLATE = "<attachment {}>"
ATTACH_PREFIX = "\n"
ATTACH_SUFFIX = "\n\n"


def attach_processor(
    annotation: Annotation,
    span_content: str,
) -> ProcessorResult:
    """Inject attachment placeholder at span start (span_content is not replaced)."""
    uid = annotation.value or ""
    replacement = ATTACH_PREFIX + ATTACH_PLACEHOLDER_TEMPLATE.format(uid) + ATTACH_SUFFIX
    return replacement, None
