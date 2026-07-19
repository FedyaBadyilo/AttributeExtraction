"""Entrypoint: context attribute grouping per eos_id.

Usage:
    python -m research.steps.context_grouping.run
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from infra.config import get_config_and_env
from infra.config.loader import config_logger
from research.datasets.access import load_class_attribute_sets, load_examples_manifest
from research.steps.attribute_grouping.domain.models import (
    AttributeGroups,
    ClassAttribute,
    ClassAttributeSet,
)
from research.steps.context_grouping.domain import build_context_attribute_groups
from research.steps.ocr.domain.models import SourceFile
from research.steps.reranking.domain.models import RerankAttribute

logger = logging.getLogger(__name__)

RERANKING_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "reranking" / "output"
ATTR_GROUPING_OUTPUT_PATH = (
    Path(__file__).resolve().parents[2] / "attribute_grouping" / "output" / "attribute_groups.json"
)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
_CLASS_ATTR_FIELDS = frozenset(ClassAttribute.model_fields)


def _to_class_attribute(raw: dict) -> ClassAttribute:
    return ClassAttribute.model_validate({k: raw[k] for k in _CLASS_ATTR_FIELDS})


def _load_attr_set(class_code: str) -> ClassAttributeSet:
    raw_sets = load_class_attribute_sets()
    if class_code not in raw_sets:
        raise ValueError(f"class_code {class_code!r} not found in class_attribute_sets.json")
    raw_attrs = raw_sets[class_code]
    attrs = {
        a.attr_id: a
        for raw in raw_attrs
        if (a := _to_class_attribute(raw)).for_extraction
    }
    if not attrs:
        raise ValueError(f"No for_extraction attributes for class {class_code!r}")
    return ClassAttributeSet(class_code=class_code, attributes=attrs)


def _load_attribute_groups_by_class() -> dict[str, AttributeGroups]:
    if not ATTR_GROUPING_OUTPUT_PATH.is_file():
        raise FileNotFoundError(f"Missing attribute groups: {ATTR_GROUPING_OUTPUT_PATH}")
    raw = json.loads(ATTR_GROUPING_OUTPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"Expected non-empty object keyed by class_code in {ATTR_GROUPING_OUTPUT_PATH}")
    return {
        class_code: AttributeGroups.model_validate(payload)
        for class_code, payload in raw.items()
    }


def main() -> None:
    config = get_config_and_env()
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]

    by_eos_id: dict[int, list[SourceFile]] = defaultdict(list)
    for sf in source_files:
        by_eos_id[sf.eos_id].append(sf)

    groups_by_class = _load_attribute_groups_by_class()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eos_ids = sorted(by_eos_id)
    total_eos = len(eos_ids)

    for i, eos_id in enumerate(eos_ids, start=1):
        entries = by_eos_id[eos_id]
        class_code = entries[0].class_code
        if class_code not in groups_by_class:
            raise ValueError(
                f"No attribute groups for class_code={class_code!r} in {ATTR_GROUPING_OUTPUT_PATH}"
            )
        attr_groups = groups_by_class[class_code]
        attr_set = _load_attr_set(class_code)

        rerank_path = RERANKING_OUTPUT_DIR / f"{eos_id}_rerank.json"
        if not rerank_path.is_file():
            raise FileNotFoundError(f"Missing rerank output: {rerank_path}")

        rerank_result = [
            RerankAttribute.model_validate(row)
            for row in json.loads(rerank_path.read_text(encoding="utf-8"))
        ]

        logger.info(
            "[%d/%d] eos_id=%s  class_code=%s  attrs=%d",
            i,
            total_eos,
            eos_id,
            class_code,
            len(attr_set.attributes),
        )
        result = build_context_attribute_groups(
            rerank_result,
            attr_set,
            config,
            attr_groups,
        )

        out_path = OUTPUT_DIR / f"{eos_id}_attribute_groups.json"
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved context groups: %d groups -> %s", len(result.groups), out_path)


if __name__ == "__main__":
    config_logger()
    main()
