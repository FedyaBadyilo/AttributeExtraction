from __future__ import annotations

_NUMERIC_TYPES = frozenset({"Вещественное число", "Диапазон", "Целое число"})
_ENUM_TYPES = frozenset({"Список", "Набор значений"})
_BOOL_VALUES = frozenset({"Да", "Нет"})


class AttrDetailsEnrichmentError(ValueError):
    pass


def parse_units(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    units = [part.strip() for part in raw.split(",") if part.strip()]
    return units or None


def parse_allowed_values(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    values = [
        part.strip()
        for part in raw.split(";")
        if part.strip() and part.strip() != "-"
    ]
    return values or None


def apply_attr_details(
    attr: dict,
    detail: dict | None,
    *,
    class_code: str,
) -> dict:
    enriched = dict(attr)

    if detail is None:
        enriched["units"] = None
        enriched["allowed_values"] = None
        return enriched

    data_type = detail.get("data_type")
    units = parse_units(detail.get("units"))
    allowed_values = (
        parse_allowed_values(detail.get("val_text"))
        if data_type in _ENUM_TYPES
        else None
    )

    if data_type in _NUMERIC_TYPES and detail.get("unit_type") and units is None:
        raise AttrDetailsEnrichmentError(
            f"missing units in attr_details for {class_code}/{attr['attr_id']} "
            f"(unit_type={detail.get('unit_type')!r})"
        )
    if data_type in _ENUM_TYPES and allowed_values is None:
        raise AttrDetailsEnrichmentError(
            f"missing allowed_values in attr_details for {class_code}/{attr['attr_id']} "
            f"({data_type})"
        )

    enriched["units"] = units
    enriched["allowed_values"] = allowed_values
    if allowed_values is not None and frozenset(allowed_values) == _BOOL_VALUES:
        enriched["attr_type"] = "bool"
    return enriched
