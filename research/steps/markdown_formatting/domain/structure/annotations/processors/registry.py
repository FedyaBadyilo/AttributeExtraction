"""
Registry of annotation processors. To add a processor: add (annotation_class, processor, inject) here.
inject=True: insert at position, do not replace span. inject=False: replace span.
"""

from typing import Any, Callable, Type

from dedoc.data_structures.annotation import Annotation
from dedoc.data_structures.concrete_annotations.attach_annotation import AttachAnnotation
from dedoc.data_structures.concrete_annotations.bold_annotation import BoldAnnotation
from dedoc.data_structures.concrete_annotations.italic_annotation import ItalicAnnotation
from dedoc.data_structures.concrete_annotations.linked_text_annotation import LinkedTextAnnotation
from dedoc.data_structures.concrete_annotations.table_annotation import TableAnnotation

from research.steps.markdown_formatting.domain.structure.annotations.processors.attach import attach_processor
from research.steps.markdown_formatting.domain.structure.annotations.processors.bold import bold_processor
from research.steps.markdown_formatting.domain.structure.annotations.processors.italic import italic_processor
from research.steps.markdown_formatting.domain.structure.annotations.processors.linked_text import linked_text_processor
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import table_processor

ProcessorEntry = tuple[Type[Annotation], Callable[..., tuple[str, dict[str, Any] | None]], bool]

PROCESSOR_REGISTRY: list[ProcessorEntry] = [
    (TableAnnotation, table_processor, True),
    (AttachAnnotation, attach_processor, True),
    (BoldAnnotation, bold_processor, False),
    (ItalicAnnotation, italic_processor, False),
    (LinkedTextAnnotation, linked_text_processor, False),
]
