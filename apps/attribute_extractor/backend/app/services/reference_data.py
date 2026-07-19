"""Reference data seed import and accessors."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.app.catalog.adapters import to_attribute_groups, to_class_attribute_set
from backend.app.catalog.models import AttributeGroupingPlanDocument, AttributesSet
from backend.app.constants import DEFAULT_OBJECT_TYPES
from backend.app.db import db_connection
from backend.app.errors import ApiError
from backend.app.settings import Settings, get_settings
from research.steps.attribute_grouping.domain.models import AttributeGroups, ClassAttributeSet

ATTRIBUTES_SET_KIND = "attributes_set"
ATTRIBUTE_GROUPING_PLAN_KIND = "attribute_grouping_plan"
MEASURE_UNITS_KIND = "measure_units_by_group"

ATTRIBUTES_SET_FILE = "attributes_set.json"
ATTRIBUTE_GROUPING_PLAN_FILE = "attribute_grouping_plan.json"
MEASURE_UNITS_FILE = "measure_units_by_group.json"


def seed_reference_data(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    measure_units = _load_seed_json(settings.reference_data_dir / MEASURE_UNITS_FILE)
    _validate_measure_units(measure_units)

    rows: list[tuple[str, str, str, str]] = []
    updated_at = datetime.now(timezone.utc).isoformat()
    for object_type, _, _ in DEFAULT_OBJECT_TYPES:
        object_dir = settings.reference_data_dir / object_type
        attributes_set = _load_seed_json(object_dir / ATTRIBUTES_SET_FILE)
        grouping_plan = _load_seed_json(object_dir / ATTRIBUTE_GROUPING_PLAN_FILE)

        _validate_attributes_set(object_type, attributes_set)
        _validate_grouping_plan(object_type, grouping_plan)

        rows.extend(
            [
                (object_type, ATTRIBUTES_SET_KIND, _to_json(attributes_set), updated_at),
                (
                    object_type,
                    ATTRIBUTE_GROUPING_PLAN_KIND,
                    _to_json(grouping_plan),
                    updated_at,
                ),
                (object_type, MEASURE_UNITS_KIND, _to_json(measure_units), updated_at),
            ]
        )

    with db_connection(settings) as connection:
        connection.executemany(
            """
            INSERT INTO reference_data (object_type, kind, payload_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(object_type, kind) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            rows,
        )


def load_reference_payload(object_type: str, kind: str) -> dict[str, Any]:
    with db_connection() as connection:
        row = connection.execute(
            """
            SELECT payload_json
            FROM reference_data
            WHERE object_type = ? AND kind = ?
            """,
            (object_type, kind),
        ).fetchone()
    if row is None:
        raise ApiError(
            status_code=404,
            code="reference_data_not_found",
            message="Reference data not found",
            details=[{"field": "object_type", "value": object_type}, {"field": "kind", "value": kind}],
        )
    return json.loads(row["payload_json"])


def load_attributes_set(object_type: str) -> AttributesSet:
    payload = load_reference_payload(object_type, ATTRIBUTES_SET_KIND)
    try:
        return AttributesSet.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(
            status_code=500,
            code="reference_data_invalid",
            message="Справочник атрибутов поврежден или устарел",
            details=[
                {
                    "field": "attributes_set",
                    "code": "reference_data_validation_failed",
                    "message": "Не удалось валидировать справочник attributes_set",
                    "details": {"object_type": object_type, "error": str(exc)},
                }
            ],
        ) from exc


def load_attribute_grouping_plan(object_type: str) -> AttributeGroupingPlanDocument:
    payload = load_reference_payload(object_type, ATTRIBUTE_GROUPING_PLAN_KIND)
    try:
        return AttributeGroupingPlanDocument.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(
            status_code=500,
            code="reference_data_invalid",
            message="План группировки атрибутов поврежден или устарел",
            details=[
                {
                    "field": "attribute_grouping_plan",
                    "code": "reference_data_validation_failed",
                    "message": "Не удалось валидировать справочник attribute_grouping_plan",
                    "details": {"object_type": object_type, "error": str(exc)},
                }
            ],
        ) from exc


def load_pipeline_attr_set(object_type: str) -> ClassAttributeSet:
    return to_class_attribute_set(load_attributes_set(object_type), object_type)


def load_pipeline_attr_groups(object_type: str) -> AttributeGroups:
    return to_attribute_groups(load_attribute_grouping_plan(object_type))


def load_measure_units_by_group(object_type: str) -> dict[str, Any]:
    return load_reference_payload(object_type, MEASURE_UNITS_KIND)


def list_seeded_reference_data() -> list[dict[str, Any]]:
    with db_connection() as connection:
        rows = connection.execute(
            """
            SELECT object_type, kind, updated_at, LENGTH(payload_json) AS size_bytes
            FROM reference_data
            ORDER BY object_type, kind
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _load_seed_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"Reference seed file not found: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid reference seed JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Reference seed JSON must contain an object: {path}")
    return payload


def _validate_attributes_set(object_type: str, payload: dict[str, Any]) -> None:
    try:
        AttributesSet.model_validate(payload)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid attributes_set seed for object_type={object_type!r}") from exc


def _validate_grouping_plan(object_type: str, payload: dict[str, Any]) -> None:
    try:
        AttributeGroupingPlanDocument.model_validate(payload)
    except ValidationError as exc:
        raise RuntimeError(
            f"Invalid attribute_grouping_plan seed for object_type={object_type!r}"
        ) from exc


def _validate_measure_units(payload: dict[str, Any]) -> None:
    groups = payload.get("groups")
    if not isinstance(groups, dict):
        raise RuntimeError("Invalid measure_units_by_group seed: missing object field 'groups'")


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
