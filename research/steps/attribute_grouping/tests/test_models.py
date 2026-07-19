from __future__ import annotations

import pytest
from pydantic import ValidationError

from research.steps.attribute_grouping.domain.models import (
    AttrType,
    AttributeGroup,
    ClassAttribute,
)


def _make(attr_type: str, **kwargs: object) -> ClassAttribute:
    return ClassAttribute.model_validate(
        {
            "attr_id": "a1",
            "attr_name": "Test",
            "descr": None,
            "attr_type": attr_type,
            "for_extraction": True,
            **kwargs,
        }
    )


def test_string_type() -> None:
    assert _make("Строка").attr_type == AttrType.STRING


def test_real_number_type() -> None:
    assert _make("Вещественное число").attr_type == AttrType.NUMBER


def test_integer_type() -> None:
    assert _make("Целое число").attr_type == AttrType.NUMBER


def test_range_type() -> None:
    assert _make("Диапазон").attr_type == AttrType.RANGE


def test_list_type() -> None:
    assert _make("Список").attr_type == AttrType.ENUM


def test_enum_list_type() -> None:
    assert _make("Набор значений").attr_type == AttrType.ENUM_LIST


def test_unknown_nci_type_raises() -> None:
    with pytest.raises(ValidationError):
        _make("UnknownType")


def test_attribute_group_rejects_empty_attr_ids() -> None:
    with pytest.raises(ValidationError):
        AttributeGroup(attr_ids=[])
