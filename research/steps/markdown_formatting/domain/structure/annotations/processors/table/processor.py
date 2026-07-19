"""Table annotation processor (inject): insert <table_ref uid="..."/> at span start."""

from dedoc.api.schema.annotation import Annotation

from research.steps.markdown_formatting.domain.structure.annotations.processors.base import ProcessorResult

TABLE_PLACEHOLDER_TEMPLATE = '<table_ref uid="{}"/>'
TABLE_PREFIX = "\n"
TABLE_SUFFIX = "\n\n"


def table_processor(
    annotation: Annotation,
    span_content: str,
) -> ProcessorResult:
    """Inject table placeholder at span start; metadata_contribution: {"tables": [uid]}."""
    uid = annotation.value
    replacement = TABLE_PREFIX + TABLE_PLACEHOLDER_TEMPLATE.format(uid) + TABLE_SUFFIX
    return replacement, {"tables": [uid]} if uid else None
