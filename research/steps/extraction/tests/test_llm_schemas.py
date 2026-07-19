from __future__ import annotations

import pytest

from research.steps.attribute_grouping.domain.models import AttrType
from research.steps.extraction.domain.llm_schemas import (
    ExtractionSchemaBool,
    ExtractionSchemaEnum,
    ExtractionSchemaEnumList,
    ExtractionSchemaNumber,
    ExtractionSchemaRange,
    ExtractionSchemaString,
    build_extraction_schema,
    build_group_extraction_response_model,
)


@pytest.mark.parametrize(
    "attr_type",
    [
        AttrType.STRING,
        AttrType.NUMBER,
        AttrType.RANGE,
        AttrType.ENUM,
        AttrType.ENUM_LIST,
        AttrType.BOOL,
    ],
)
def test_build_extraction_schema_returns_model_per_attr_type(attr_type: AttrType) -> None:
    schema = build_extraction_schema(
        attr_type,
        2,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    assert schema.__name__.startswith("_FinalSchema")
    assert "source_chunk" in schema.model_fields
    assert "raw_quote" in schema.model_fields
    assert "value" in schema.model_fields


def test_source_chunk_enum_from_chunk_count() -> None:
    schema = build_extraction_schema(
        AttrType.STRING,
        3,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    json_schema = schema.model_json_schema()
    source_chunk = json_schema["properties"]["source_chunk"]
    assert source_chunk["enum"] == [1, 2, 3, None]


def test_enum_schema_value_field_has_allowed_values_constraint() -> None:
    schema = build_extraction_schema(
        AttrType.ENUM,
        1,
        has_unit=False,
        allowed_values=["A", "B"],
        units=None,
    )
    json_schema = schema.model_json_schema()
    value_field = json_schema["properties"]["value"]
    assert value_field["enum"] == ["A", "B", None]


def test_enum_list_schema_value_field_type() -> None:
    schema = build_extraction_schema(
        AttrType.ENUM_LIST,
        1,
        has_unit=False,
        allowed_values=["X", "Y"],
        units=None,
    )
    value_annotation = schema.model_fields["value"].annotation
    assert value_annotation == list[str] | None
    json_schema = schema.model_json_schema()
    assert json_schema["properties"]["value"]["items"]["enum"] == ["X", "Y"]


def test_build_group_extraction_response_model_tuple_length() -> None:
    s1 = build_extraction_schema(
        AttrType.STRING,
        1,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    s2 = build_extraction_schema(
        AttrType.NUMBER,
        1,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    group_model = build_group_extraction_response_model([s1, s2])
    extractions_field = group_model.model_fields["extractions"]
    assert extractions_field.annotation == tuple[s1, s2]

    instance = group_model.model_validate(
        {
            "extractions": (
                {"source_chunk": 1, "value": "x", "raw_quote": "q"},
                {"source_chunk": None, "value": 42, "raw_quote": None},
            )
        }
    )
    assert len(instance.extractions) == 2


def test_base_schema_classes_exist() -> None:
    assert ExtractionSchemaString.model_fields["value"].annotation == str | None
    assert ExtractionSchemaNumber.model_fields["value"].annotation == int | float | None
    assert ExtractionSchemaRange.model_fields["value"].annotation == list[float] | None
    assert ExtractionSchemaEnum.model_fields["value"].annotation == str | None
    assert ExtractionSchemaEnumList.model_fields["value"].annotation == list[str] | None
    assert ExtractionSchemaBool.model_fields["value"].annotation == bool | None


def test_range_value_rejects_min_greater_than_max() -> None:
    with pytest.raises(ValueError, match="min must be <= max"):
        ExtractionSchemaRange(source_chunk=None, value=[10.0, 1.0])


def test_range_schema_accepts_null_value() -> None:
    schema = build_extraction_schema(
        AttrType.RANGE,
        2,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    item = schema.model_validate(
        {
            "source_chunk": None,
            "value": None,
            "raw_quote": None,
        }
    )
    assert item.value is None


def test_range_schema_accepts_bounds() -> None:
    schema = build_extraction_schema(
        AttrType.RANGE,
        2,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    item = schema.model_validate(
        {
            "source_chunk": 1,
            "value": [0.0, 70.0],
            "raw_quote": "0‡70",
        }
    )
    assert item.value == [0.0, 70.0]


def test_range_schema_rejects_partial_bounds() -> None:
    schema = build_extraction_schema(
        AttrType.RANGE,
        2,
        has_unit=False,
        allowed_values=None,
        units=None,
    )
    with pytest.raises(ValueError):
        schema.model_validate(
            {
                "source_chunk": None,
                "value": [0.0],
                "raw_quote": None,
            }
        )
