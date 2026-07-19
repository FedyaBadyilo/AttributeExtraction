from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AttrType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    RANGE = "range"
    ENUM = "enum"
    ENUM_LIST = "enum_list"
    BOOL = "bool"


_NCI_TYPE_MAP: dict[str, AttrType] = {
    "Строка": AttrType.STRING,
    "Вещественное число": AttrType.NUMBER,
    "Целое число": AttrType.NUMBER,
    "Диапазон": AttrType.RANGE,
    "Список": AttrType.ENUM,
    "Набор значений": AttrType.ENUM_LIST,
}


class ClassAttribute(BaseModel):
    model_config = {"extra": "forbid"}

    attr_id: str
    attr_name: str = Field(min_length=1)
    descr: str | None = None
    attr_type: AttrType
    for_extraction: bool
    units: list[str] | None = None
    allowed_values: list[str] | None = None

    @field_validator("attr_type", mode="before")
    @classmethod
    def _map_nci_type(cls, v: object) -> AttrType:
        if isinstance(v, AttrType):
            return v
        if not isinstance(v, str):
            raise ValueError(f"Unknown attribute type: {v!r}")
        try:
            return AttrType(v)
        except ValueError:
            pass
        if v not in _NCI_TYPE_MAP:
            raise ValueError(f"Unknown attribute type: {v!r}")
        return _NCI_TYPE_MAP[v]


class AttributeGroup(BaseModel):
    attr_ids: list[str] = Field(min_length=1)


class AttributeGroups(BaseModel):
    groups: list[AttributeGroup]


class ClassAttributeSet(BaseModel):
    """Full set of extractable attributes for one NSI class."""

    class_code: str
    attributes: dict[str, ClassAttribute]  # attr_id → ClassAttribute (for_extraction=True)
