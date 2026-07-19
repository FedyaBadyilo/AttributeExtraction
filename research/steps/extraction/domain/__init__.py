from __future__ import annotations

from typing import Any

from research.steps.extraction.domain.models import (
    ExtractedAttributeItem,
    ExtractedAttributesDocument,
)

__all__ = [
    "ExtractedAttributeItem",
    "ExtractedAttributesDocument",
    "run_extraction",
]


def __getattr__(name: str) -> Any:
    if name == "run_extraction":
        from research.steps.extraction.domain.runner import run_extraction

        return run_extraction
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
