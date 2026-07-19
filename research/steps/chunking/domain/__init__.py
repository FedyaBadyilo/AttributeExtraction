from __future__ import annotations

from typing import Any

__all__ = ["chunk_document"]


def __getattr__(name: str) -> Any:
    if name == "chunk_document":
        from research.steps.chunking.domain.runner import chunk_document

        return chunk_document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
