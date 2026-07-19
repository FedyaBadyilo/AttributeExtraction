"""Entrypoint: attribute extraction per eos_id.

Usage:
    python -m research.steps.extraction.run
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from infra.config import get_config_and_env
from infra.config.loader import config_logger
from research.datasets.access import load_class_attribute_sets, load_examples_manifest
from research.steps.attribute_grouping.domain.models import ClassAttribute, ClassAttributeSet
from research.steps.context_rebuild.domain.models import GroupedContextResult
from research.steps.extraction.domain import run_extraction
from research.steps.ocr.domain.models import SourceFile
from research.steps.retrieval.domain.models import AttributeSearchResult
from research.steps.retrieval.domain.query import normalize_execution_variant

logger = logging.getLogger(__name__)

RETRIEVAL_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "retrieval" / "output"
CONTEXT_REBUILD_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "context_rebuild" / "output"
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


def main() -> None:
    config = get_config_and_env()
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]
    priority_by_filename = {sf.pdf_filename: sf.file_priority for sf in source_files}

    by_eos_id: dict[int, list[SourceFile]] = defaultdict(list)
    for sf in source_files:
        by_eos_id[sf.eos_id].append(sf)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eos_ids = sorted(by_eos_id)
    total_eos = len(eos_ids)

    for i, eos_id in enumerate(eos_ids, start=1):
        entries = by_eos_id[eos_id]
        class_code = entries[0].class_code
        attr_set = _load_attr_set(class_code)

        search_path = RETRIEVAL_OUTPUT_DIR / f"{eos_id}_search.json"
        if not search_path.is_file():
            raise FileNotFoundError(f"Missing retrieval search output: {search_path}")

        search_rows = [
            AttributeSearchResult.model_validate(row)
            for row in json.loads(search_path.read_text(encoding="utf-8"))
        ]
        priority_by_point_id = {
            hit.id: priority_by_filename.get(hit.payload.metadata.file_name, 0)
            for row in search_rows
            for hit in row.chunks
        }

        context_path = CONTEXT_REBUILD_OUTPUT_DIR / f"{eos_id}_extraction_context.json"
        if not context_path.is_file():
            raise FileNotFoundError(f"Missing context rebuild output: {context_path}")

        grouped = GroupedContextResult.model_validate_json(context_path.read_text(encoding="utf-8"))
        execution_variant = _execution_variant_for_eos(entries)

        logger.info(
            "[%d/%d] eos_id=%s  attrs=%d  execution_variant=%s",
            i,
            total_eos,
            eos_id,
            len(attr_set.attributes),
            execution_variant,
        )
        result = run_extraction(
            grouped,
            attr_set,
            config,
            priority_by_point_id=priority_by_point_id,
            execution_variant=execution_variant,
        )
        out_path = OUTPUT_DIR / f"{eos_id}_extraction.json"
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        logger.info(
            "Saved extraction: %d attrs -> %s",
            len(result.extractions),
            out_path,
        )


if __name__ == "__main__":
    config_logger()
    main()
