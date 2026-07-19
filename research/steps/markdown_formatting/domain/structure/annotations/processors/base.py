"""
Contract for annotation processors: (replacement_text, metadata_contribution).
Processors receive span_content (current content of [start:end]) and return replacement.
Replace-type: replacement overwrites the span. Inject-type: replacement is inserted at start, span kept.
Metadata_contribution is a dict merged into FormattedNodeMetadata at the same level (e.g. {"tables": [uid]}).
"""

from __future__ import annotations

from typing import Any, Protocol

from dedoc.api.schema.annotation import Annotation

ProcessorResult = tuple[str, dict[str, Any] | None]


class AnnotationProcessor(Protocol):
    """Process one annotation: (annotation, span_content) -> (replacement, metadata_contribution dict or None)."""

    def __call__(
        self,
        annotation: Annotation,
        span_content: str,
    ) -> ProcessorResult: ...
