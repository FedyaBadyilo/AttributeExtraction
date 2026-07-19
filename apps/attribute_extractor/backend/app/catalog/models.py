"""Backend-owned catalog models for SQLite seed JSON (attributes_set / grouping plan)."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValueType:
    STRING = "string"
    NUMBER = "number"
    ENUM = "enum"
    BOOL = "bool"

    _ALIASES: dict[str, str] = {
        "str": STRING,
        "string": STRING,
        "number": NUMBER,
        "real": NUMBER,
        "integer": NUMBER,
        "enum": ENUM,
        "bool": BOOL,
        "boolean": BOOL,
    }

    @classmethod
    def normalize(cls, value: str | None) -> str:
        if not value:
            return cls.STRING
        key = str(value).strip().lower()
        return cls._ALIASES.get(key, str(value).strip())


class AttributeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attribute_name: str = Field(min_length=1)
    altnames: list[str] = Field(default_factory=list)
    description: str | None = None
    rag_hint: str | None = None
    extraction_hint: str | None = None
    value_type: str = Field(default=ValueType.STRING)
    is_large: bool = False
    has_unit: bool = False
    enum_list: list[str] | None = None
    code_unit: str | None = None
    essential: bool
    for_extraction: bool = True
    unit_enum_list: list[str] | None = None

    @field_validator("value_type", mode="before")
    @classmethod
    def _normalize_value_type(cls, v: str | None) -> str:
        return ValueType.normalize(v)


class AttributesSet(BaseModel):
    attributes: dict[str, AttributeItem] = Field(default_factory=dict)

    def for_extraction_only(self) -> Self:
        return self.__class__(
            attributes={k: v for k, v in self.attributes.items() if v.for_extraction}
        )


class SemanticGroup(BaseModel):
    attribute_ids: list[str] = Field(default_factory=list)


class AttributeGroupingPlanDocument(BaseModel):
    semantic_groups: list[SemanticGroup] = Field(default_factory=list)
