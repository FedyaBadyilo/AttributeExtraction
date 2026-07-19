from __future__ import annotations

from typing import Any

from typing_extensions import Self

from pydantic import BaseModel, Field, create_model, model_validator

from research.steps.attribute_grouping.domain.models import AttrType

RAW_QUOTE_DESCRIPTION = (
    "Exactly one line from the source where the answer was taken. If the source passage is long, "
    "use only the first line. Copy verbatim — no explanation. When value is null, use null."
)

SOURCE_CHUNK_FIELD_TITLE = "Primary evidence chunk"

SOURCE_CHUNK_DESCRIPTION = (
    '`<chunk number="N">` → **N** only from this field\'s JSON Schema **enum**.'
    "If value is **null** ⇒ source_chunk must be **null**. "
    "If value is **set** ⇒ source_chunk always must be that set with index of the chunk that contains the value."
)


class ExtractionResponseBase(BaseModel):
    source_chunk: int | None = Field(
        title=SOURCE_CHUNK_FIELD_TITLE,
        description=SOURCE_CHUNK_DESCRIPTION,
    )


UNIT_FIELD = (
    str | None,
    Field(
        description=(
            "Unit of measurement copied verbatim from the source text — "
            "preserve the exact characters, language, and notation as they appear "
            "(e.g. if source shows 'yr', output 'yr'; if source shows 'кг', output 'кг'). "
            "Do not translate, convert, or normalize. "
            "Null if no unit is present or value is null."
        ),
    ),
)

UNIT_FIELD_ENUM_DESCRIPTION = (
    "Unit of measurement: must be exactly one of the allowed symbols in the schema enum"
    "Null if value is null."
)


def _unit_field_from_enum(allowed: list[str]) -> tuple[Any, Any]:
    uniq = list(dict.fromkeys(allowed))
    return (
        str | None,
        Field(
            default=None,
            description=UNIT_FIELD_ENUM_DESCRIPTION,
            json_schema_extra={"enum": uniq + [None]},
        ),
    )


class ExtractionSchemaString(ExtractionResponseBase):
    value: str | None = Field(
        max_length=2000,
        description=(
            "Exact string from context (name/code/designation/phrase). "
            "Copy without paraphrasing or truncation. Null if not explicitly present."
        ),
    )


class ExtractionSchemaNumber(ExtractionResponseBase):
    value: int | float | None = Field(
        description=(
            "Numeric value stated in context (dot as decimal separator). "
            "If the source provides a range/bound (e.g. 'не менее', 'от...до'), extract the value that directly answers "
            "the attribute as stated; if unclear, return null."
        ),
    )


class ExtractionSchemaRange(ExtractionResponseBase):
    value: list[float] | None = Field(
        default=None,
        min_length=2,
        max_length=2,
        description=(
            "Numeric range as [min, max] stated in context. "
            "Null if the range is not explicitly present."
        ),
    )

    @model_validator(mode="after")
    def min_lte_max(self) -> Self:
        if self.value is not None and self.value[0] > self.value[1]:
            raise ValueError("min must be <= max")
        return self


class ExtractionSchemaEnum(ExtractionResponseBase):
    value: str | None = Field(
        max_length=2000,
        description=(
            "Must match exactly one allowed enum value (character-for-character, no normalization). "
            "Null if not explicitly present."
        ),
    )


class ExtractionSchemaEnumList(ExtractionResponseBase):
    value: list[str] | None = Field(
        description=(
            "List of enum values explicitly stated in context. Each item must match one allowed enum value "
            "(character-for-character). Null if not explicitly present."
        ),
    )


class ExtractionSchemaBool(ExtractionResponseBase):
    value: bool | None = Field(
        description=(
            "Return true/false only if the context gives an explicit binary statement "
            "(yes/no, present/absent, required/not required). Otherwise null."
        ),
    )


def _base_schema_for_attr_type(attr_type: AttrType) -> type[BaseModel]:
    if attr_type == AttrType.STRING:
        return ExtractionSchemaString
    if attr_type == AttrType.NUMBER:
        return ExtractionSchemaNumber
    if attr_type == AttrType.RANGE:
        return ExtractionSchemaRange
    if attr_type == AttrType.ENUM:
        return ExtractionSchemaEnum
    if attr_type == AttrType.ENUM_LIST:
        return ExtractionSchemaEnumList
    if attr_type == AttrType.BOOL:
        return ExtractionSchemaBool
    raise ValueError(f"Unsupported attr_type: {attr_type}")


def build_extraction_schema(
    attr_type: AttrType,
    chunk_count: int,
    *,
    has_unit: bool,
    allowed_values: list[str] | None,
    units: list[str] | None,
) -> type[BaseModel]:
    base_class = _base_schema_for_attr_type(attr_type)

    if has_unit:
        allowed = [s for s in (units or []) if s and str(s).strip()]
        if allowed:
            base_class = create_model(
                f"{base_class.__name__}WithUnitEnum",
                __base__=base_class,
                unit=_unit_field_from_enum(allowed),
            )
        else:
            base_class = create_model(f"{base_class.__name__}WithUnit", __base__=base_class, unit=UNIT_FIELD)

    if attr_type == AttrType.ENUM and allowed_values:

        class _EnumWithValues(base_class):
            value: str | None = Field(
                max_length=2000,
                description=(
                    "Must match exactly one allowed enum value (character-for-character, no normalization). "
                    "If multiple apply, choose the one whose label match is most precise; if unsure, null."
                ),
                json_schema_extra={"enum": allowed_values + [None]},
            )

        _EnumWithValues.model_rebuild()
        base_class = _EnumWithValues

    if attr_type == AttrType.ENUM_LIST and allowed_values:

        class _EnumListWithValues(base_class):
            value: list[str] | None = Field(
                description=(
                    "List of enum values explicitly stated in context. Each item must match one allowed enum value "
                    "(character-for-character). Null if not explicitly present."
                ),
                json_schema_extra={"items": {"type": "string", "enum": allowed_values}},
            )

        _EnumListWithValues.model_rebuild()
        base_class = _EnumListWithValues

    if chunk_count > 0:
        chunk_indices = list(range(1, chunk_count + 1))

        class _WithChunks(base_class):
            source_chunk: int | None = Field(
                title=SOURCE_CHUNK_FIELD_TITLE,
                description=SOURCE_CHUNK_DESCRIPTION,
                json_schema_extra={"enum": chunk_indices + [None]},
            )

        _WithChunks.model_rebuild()
        base_class = _WithChunks

    class _FinalSchema(base_class):
        raw_quote: str | None = Field(
            max_length=2000,
            description=RAW_QUOTE_DESCRIPTION,
        )

    _FinalSchema.model_rebuild()
    return _FinalSchema


def build_group_extraction_response_model(
    attr_schemas: list[type[BaseModel]],
) -> type[BaseModel]:
    if not attr_schemas:

        class _EmptyGroupExtractionResponse(BaseModel):
            extractions: tuple[()] = ()

        _EmptyGroupExtractionResponse.model_rebuild()
        return _EmptyGroupExtractionResponse

    tuple_type = tuple.__class_getitem__(tuple(attr_schemas))
    model = create_model(
        "GroupExtractionResponseTyped",
        extractions=(
            tuple_type,
            Field(
                description=(
                    "Tuple in the same order as <attributes> in the prompt: position i = attribute "
                    'with index="i" (0-based). Put each value only in its own position; do not '
                    "swap slots. Use null where there is no value for that attribute."
                )
            ),
        ),
    )
    model.model_rebuild()
    return model
