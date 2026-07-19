"""Ground truth loading and labeling task construction."""

from __future__ import annotations

from typing import Any

from research.datasets.access import load_ground_truth
from research.datasets.build.ground_truth import is_empty_ground_truth_value

from apps.rag_labeling.config_paths import (
    get_attributes_set_order,
    get_class_attribute,
    get_class_code,
    get_source_files_for_eos,
)

def normalize_execution_variant(execution_variant: Any) -> str | None:
    if execution_variant is None:
        return None
    value = str(execution_variant).strip()
    if not value:
        return None
    if value.lower() in {"none", "null", "n/a"}:
        return None
    return value


def is_empty(value: object) -> bool:
    """Return True when a ground-truth value should be excluded from labeling tasks."""
    return is_empty_ground_truth_value(value)


def execution_variant_for_eos(eos_id: int) -> str | None:
    """Pick execution variant from manifest entries with highest file_priority."""
    entries = get_source_files_for_eos(eos_id)
    for sf in sorted(entries, key=lambda row: row.file_priority, reverse=True):
        variant = normalize_execution_variant(sf.variant_execution_id)
        if variant:
            return variant
    return None


def _ground_truth_by_gid() -> dict[int, dict[str, dict]]:
    by_gid: dict[int, dict[str, dict]] = {}
    for row in load_ground_truth():
        gid = int(row["gid"])
        attr_id = row["attr_id"]
        by_gid.setdefault(gid, {})[attr_id] = row
    return by_gid


_GT_BY_GID: dict[int, dict[str, dict]] | None = None


def _get_gt_by_gid() -> dict[int, dict[str, dict]]:
    global _GT_BY_GID
    if _GT_BY_GID is None:
        _GT_BY_GID = _ground_truth_by_gid()
    return _GT_BY_GID


def build_tasks(eos_id: int) -> list[dict]:
    """Build labeling tasks for one eos_id document."""
    class_code = get_class_code(eos_id)
    order = get_attributes_set_order(class_code)
    gt_rows = _get_gt_by_gid().get(eos_id, {})

    tasks: list[dict] = []
    for attr_id in order:
        row = gt_rows.get(attr_id)
        if row is None or is_empty(row["value"]):
            continue
        attr = get_class_attribute(class_code, attr_id)
        tasks.append({
            "eos_id": eos_id,
            "attr_id": attr_id,
            "attr_name": row["attr_name"],
            "value": row["value"],
            "descr": attr.descr,
            "class_code": class_code,
        })
    return tasks
