"""Concrete benchmark pipelines."""

from research.benchmarks.document_parsing.pipelines.dedoc import (
    render_formatted_document,
    run_dedoc_pipeline,
)

__all__ = ["render_formatted_document", "run_dedoc_pipeline"]
