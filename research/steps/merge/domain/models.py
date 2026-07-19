"""Data models for merge step: merged context blocks for downstream steps."""

from pydantic import BaseModel, Field, field_validator


class MergedChunk(BaseModel):
    """One merged context block after structure/table merge."""

    source_point_ids: tuple[int, ...] = Field(description="Canonical Qdrant point ids included in content")
    display_point_id: int = Field(description="Primary Qdrant point id for this merged block")
    content: str = Field(description="Merged markdown/text passed to downstream extraction")
    header_path: list[str] = Field(default_factory=list)
    section_id: int = Field(
        description=(
            "Structure chunk point id this block belongs to. "
            "Same for all blocks built from the same section; "
            "equals display_point_id for structure hits."
        )
    )

    @field_validator("source_point_ids", mode="before")
    @classmethod
    def _canonicalize_source_point_ids(cls, value: object) -> tuple[int, ...]:
        return tuple(sorted({int(point_id) for point_id in value}))


class MergeResult(BaseModel):
    """One attribute after context merge."""

    attribute_id: str = Field(description="Attribute id")
    merged_chunks: list[MergedChunk] = Field(
        default_factory=list,
        description="Merged blocks for this attribute in merge order",
    )
