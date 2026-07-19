from __future__ import annotations

from pydantic import BaseModel


class SourceFile(BaseModel):
    """One entry from examples_manifest.json: one PDF file associated with an EOS record."""

    eos_id: int
    pdf_filename: str
    file_priority: int
    variant_execution_id: str | None
    class_code: str
