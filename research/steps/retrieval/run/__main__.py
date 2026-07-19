"""Entrypoint: hybrid search per eos_id collection.

Usage:
    python -m research.steps.retrieval.run
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from infra.config import get_config_and_env
from infra.config.loader import config_logger
from research.datasets.access import load_class_attribute_sets, load_examples_manifest
from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.ocr.domain.models import SourceFile
from research.steps.retrieval.domain import run_retrieval
from research.steps.retrieval.domain.query import normalize_execution_variant

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
_CLASS_ATTR_FIELDS = frozenset(ClassAttribute.model_fields)


def _to_class_attribute(raw: dict) -> ClassAttribute:
    return ClassAttribute.model_validate({k: raw[k] for k in _CLASS_ATTR_FIELDS})


def _execution_variant_for_eos(entries: list[SourceFile]) -> str | None:
    for sf in sorted(entries, key=lambda row: row.file_priority, reverse=True):
        variant = normalize_execution_variant(sf.variant_execution_id)
        if variant:
            return variant
    return None


def _load_attrs_for_class(class_code: str) -> dict[str, ClassAttribute]:
    raw_sets = load_class_attribute_sets()
    if class_code not in raw_sets:
        raise ValueError(f"class_code {class_code!r} not found in class_attribute_sets.json")
    attrs_by_id = {
        a.attr_id: a
        for raw in raw_sets[class_code]
        if (a := _to_class_attribute(raw)).for_extraction
    }
    if not attrs_by_id:
        raise ValueError(f"No for_extraction attributes for class {class_code!r}")
    return attrs_by_id


def main() -> None:
    config = get_config_and_env()
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]

    by_eos_id: dict[int, list[SourceFile]] = defaultdict(list)
    for sf in source_files:
        by_eos_id[sf.eos_id].append(sf)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eos_ids = sorted(by_eos_id)
    total_eos = len(eos_ids)

    for i, eos_id in enumerate(eos_ids, start=1):
        entries = by_eos_id[eos_id]
        class_code = entries[0].class_code
        attrs_by_id = _load_attrs_for_class(class_code)
        collection_name = config["QDRANT_COLLECTION_TEMPLATE"].format(eos_id=eos_id)
        execution_variant = _execution_variant_for_eos(entries)
        logger.info(
            "[%d/%d] eos_id=%s  class_code=%s  attrs=%d  execution_variant=%s  collection=%s",
            i,
            total_eos,
            eos_id,
            class_code,
            len(attrs_by_id),
            execution_variant,
            collection_name,
        )
        results = run_retrieval(
            attrs_by_id,
            collection_name,
            config,
            execution_variant=execution_variant,
        )
        out_path = OUTPUT_DIR / f"{eos_id}_search.json"
        payload = [result.model_dump(mode="json") for result in results]
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Saved %d attribute results -> %s", len(results), out_path)


if __name__ == "__main__":
    config_logger()
    main()
