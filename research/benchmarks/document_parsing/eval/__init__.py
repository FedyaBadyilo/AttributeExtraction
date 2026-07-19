"""MLflow evaluation wiring for the document parsing benchmark."""

from research.benchmarks.document_parsing.eval.adapter import (
    DocumentParsingEvalAdapter,
    RebuildDocumentParsingEvalAdapter,
)

__all__ = ["DocumentParsingEvalAdapter", "RebuildDocumentParsingEvalAdapter"]
