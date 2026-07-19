from __future__ import annotations

import re
from typing import Any

_RANGE_SEPARATOR = "‡"
_RANGE_ATTR_TYPE = "Диапазон"

_PLACEHOLDER_VALUES = frozenset({
    "-",
    "—",
    "–",
    "-‡-",
    "n/a",
    "na",
    "null",
    "none",
    "нет",
    "н/д",
    "н\\д",
})


def parse_nci_number(text: str) -> float:
    return float(text.strip().replace(",", "."))


def parse_nci_range_value(value: str) -> list[float]:
    parts = value.split(_RANGE_SEPARATOR)
    if len(parts) == 1:
        scalar = parse_nci_number(parts[0])
        return [scalar, scalar]
    if len(parts) == 2:
        return [parse_nci_number(parts[0]), parse_nci_number(parts[1])]
    raise ValueError(f"Invalid NCI range value: {value!r}")


def is_empty_ground_truth_value(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    normalized = re.sub(r"\s+", "", text).lower()
    return normalized in _PLACEHOLDER_VALUES


def normalize_ground_truth_row(
    row: dict[str, Any],
    *,
    attr_type: str | None = None,
) -> dict[str, Any]:
    normalized = dict(row)
    value = normalized.get("value")
    if is_empty_ground_truth_value(value):
        normalized["value"] = None
        return normalized

    if attr_type == _RANGE_ATTR_TYPE:
        if isinstance(value, list):
            if len(value) == 1:
                scalar = float(value[0])
                normalized["value"] = [scalar, scalar]
            elif len(value) == 2:
                normalized["value"] = [float(value[0]), float(value[1])]
            else:
                raise ValueError(
                    f"Invalid preprocessed range for gid={row.get('gid')}, "
                    f"attr_id={row.get('attr_id')}: {value!r}"
                )
        elif isinstance(value, str):
            normalized["value"] = parse_nci_range_value(value)
        else:
            raise ValueError(
                f"Unsupported range ground truth value for gid={row.get('gid')}, "
                f"attr_id={row.get('attr_id')}: {value!r}"
            )

    return normalized


def materialize_missing_extraction_slots(
    *,
    gid_to_class: dict[int, str],
    class_attribute_sets: dict[str, list[dict[str, Any]]],
    ground_truth_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Append ``value=null`` rows for for_extraction slots absent from NCI.

    NCI often omits unused class-template attributes entirely. For eval that is
    equivalent to an explicit empty placeholder (``-`` → null), so we materialize
    missing slots instead of dropping otherwise well-filled cards.
    """
    present = {(int(row["gid"]), str(row["attr_id"])) for row in ground_truth_rows}
    materialized = list(ground_truth_rows)
    for gid, class_code in sorted(gid_to_class.items()):
        for attr in class_attribute_sets[class_code]:
            if not attr["for_extraction"]:
                continue
            attr_id = str(attr["attr_id"])
            if (gid, attr_id) in present:
                continue
            materialized.append(
                {
                    "gid": gid,
                    "attr_id": attr_id,
                    "attr_name": attr["attr_name"],
                    "value": None,
                }
            )
            present.add((gid, attr_id))
    return materialized


def assert_extraction_slots_have_ground_truth(
    *,
    gid_to_class: dict[int, str],
    class_attribute_sets: dict[str, list[dict[str, Any]]],
    ground_truth_rows: list[dict[str, Any]],
) -> None:
    """Fail if any for_extraction slot lacks a GT row.

    Empty values must be present as rows with ``value=null``, not omitted.
    Call :func:`materialize_missing_extraction_slots` first when NCI omits slots.
    """
    present = {(int(row["gid"]), str(row["attr_id"])) for row in ground_truth_rows}
    missing: list[str] = []
    for gid, class_code in sorted(gid_to_class.items()):
        attrs = class_attribute_sets[class_code]
        for attr in attrs:
            if not attr["for_extraction"]:
                continue
            attr_id = str(attr["attr_id"])
            if (gid, attr_id) in present:
                continue
            missing.append(
                f"gid={gid}, attr_id={attr_id}, attr_name={attr['attr_name']!r}, "
                f"class_code={class_code!r}"
            )
    if missing:
        preview = "\n".join(f"  - {item}" for item in missing[:20])
        more = "" if len(missing) <= 20 else f"\n  ... and {len(missing) - 20} more"
        raise ValueError(
            f"Missing ground truth for {len(missing)} for_extraction slot(s):\n"
            f"{preview}{more}"
        )
