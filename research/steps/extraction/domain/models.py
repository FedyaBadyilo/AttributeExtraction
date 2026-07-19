from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ExtractedAttributeItem(BaseModel):
    attribute_id: str
    value: str | int | float | bool | list[str] | list[float | None] | None = None
    unit: str | None = None
    source_section_id: int | None = None
    top_rerank_section_id: int | None = None
    rerank_score: float | None = None
    high_confidence: bool | None = None
    raw_quote: str | None = None
    error: bool = False
    reasoning: str | None = None
    # Set by extraction runner for attrs with units; excluded from serialized artifacts.
    requires_unit: bool = Field(default=False, exclude=True)

    @model_validator(mode="after")
    def _normalize_nullable_fields(self) -> ExtractedAttributeItem:
        if self.value is None:
            self.source_section_id = None
            self.unit = None
        else:
            self.top_rerank_section_id = None
            if self.requires_unit and self.unit is None and not self.error:
                raise ValueError(
                    f"unit is required when value is set for attribute {self.attribute_id!r}"
                )
        return self


class ExtractedAttributesDocument(BaseModel):
    extractions: list[ExtractedAttributeItem] = Field(default_factory=list)
