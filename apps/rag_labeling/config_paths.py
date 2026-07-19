"""Paths and dataset helpers for RAG labeling app."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAG_LABELING_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from research.datasets.access import (  # noqa: E402
    EXAMPLES_MANIFEST_FILENAME,
    PROCESSED_DIR,
    RAG_LABELS_DIR,
    load_class_attribute_sets,
    load_examples_manifest,
)
from research.steps.attribute_grouping.domain.models import ClassAttribute  # noqa: E402
from research.steps.ocr.domain.models import SourceFile  # noqa: E402

RAG_LABELS_CACHE_DIR = RAG_LABELING_DIR / ".cache" / "rag_labels"
RAG_PIPELINE_CACHE_DIR = RAG_LABELING_DIR / ".cache" / "rag_pipeline"

_CLASS_ATTR_FIELDS = frozenset(ClassAttribute.model_fields)


def _to_class_attribute(raw: dict) -> ClassAttribute:
    return ClassAttribute.model_validate({k: raw[k] for k in _CLASS_ATTR_FIELDS})


def _manifest_entries() -> list[SourceFile]:
    """Load manifest when present; empty list if processed pack is not installed yet."""
    path = PROCESSED_DIR / EXAMPLES_MANIFEST_FILENAME
    if not path.is_file():
        return []
    return [SourceFile.model_validate(e) for e in load_examples_manifest()]


def _eos_id_to_class_code() -> dict[int, str]:
    mapping: dict[int, str] = {}
    for sf in _manifest_entries():
        mapping[sf.eos_id] = sf.class_code
    return mapping


def _source_files_by_eos() -> dict[int, list[SourceFile]]:
    by_eos: dict[int, list[SourceFile]] = defaultdict(list)
    for sf in _manifest_entries():
        by_eos[sf.eos_id].append(sf)
    return dict(by_eos)


_EOS_TO_CLASS = _eos_id_to_class_code()
_SOURCE_FILES_BY_EOS = _source_files_by_eos()
EOS_IDS = sorted(_SOURCE_FILES_BY_EOS)


def get_class_code(eos_id: int) -> str:
    return _EOS_TO_CLASS[eos_id]


def get_source_files_for_eos(eos_id: int) -> list[SourceFile]:
    return _SOURCE_FILES_BY_EOS[eos_id]


def get_attributes_set_order(class_code: str) -> list[str]:
    raw_sets = load_class_attribute_sets()
    out: list[str] = []
    for raw in raw_sets[class_code]:
        if raw.get("for_extraction", True):
            out.append(raw["attr_id"])
    return out


def get_class_attribute(class_code: str, attr_id: str) -> ClassAttribute:
    raw_sets = load_class_attribute_sets()
    for raw in raw_sets[class_code]:
        if raw["attr_id"] == attr_id:
            return _to_class_attribute(raw)
    raise KeyError(f"attr_id {attr_id!r} not found in class {class_code!r}")
