from __future__ import annotations

from pathlib import Path
from typing import Any

from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.extraction.domain.models import ExtractedAttributesDocument
from research.steps.extraction.eval.models import EvalAttribute, GroundTruthSlot, PredictionSlot

_CLASS_ATTR_FIELDS = frozenset(ClassAttribute.model_fields)


def _to_class_attribute(raw: dict[str, Any]) -> ClassAttribute:
    return ClassAttribute.model_validate({k: raw[k] for k in _CLASS_ATTR_FIELDS})


def _extractable_attrs_by_class(raw_sets: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, ClassAttribute]]:
    by_class: dict[str, dict[str, ClassAttribute]] = {}
    for class_code, raw_attrs in raw_sets.items():
        attrs = {}
        for raw in raw_attrs:
            attr = _to_class_attribute(raw)
            if attr.for_extraction:
                attrs[attr.attr_id] = attr
        by_class[class_code] = attrs
    return by_class


def build_eval_universe(
    examples: list[dict[str, Any]],
    raw_class_attribute_sets: dict[str, list[dict[str, Any]]],
) -> list[EvalAttribute]:
    attrs_by_class = _extractable_attrs_by_class(raw_class_attribute_sets)
    universe: list[EvalAttribute] = []
    for example in examples:
        eos_id = int(example["eos_id"])
        class_code = str(example["class_code"])
        if class_code not in attrs_by_class:
            raise ValueError(f"class_code {class_code!r} not found in class_attribute_sets")
        for attr in attrs_by_class[class_code].values():
            universe.append(
                EvalAttribute(
                    eos_id=eos_id,
                    class_code=class_code,
                    attr_id=attr.attr_id,
                    attr_name=attr.attr_name,
                    attr_type=attr.attr_type,
                    has_unit=attr.units is not None,
                )
            )
    return universe


def build_ground_truth_index(rows: list[dict[str, Any]]) -> dict[tuple[int, str], GroundTruthSlot]:
    index: dict[tuple[int, str], GroundTruthSlot] = {}
    for row in rows:
        eos_id = int(row["gid"])
        attr_id = str(row["attr_id"])
        key = (eos_id, attr_id)
        if key in index:
            raise ValueError(f"Duplicate GT row for eos_id={eos_id}, attr_id={attr_id}")
        raw_unit = row.get("unit")
        unit = None if raw_unit is None else str(raw_unit).strip() or None
        index[key] = GroundTruthSlot(
            eos_id=eos_id,
            attr_id=attr_id,
            attr_name=str(row["attr_name"]),
            value=row["value"],
            unit=unit,
        )
    return index


def load_prediction_document(path: Path, eos_id: int) -> dict[str, PredictionSlot]:
    document = ExtractedAttributesDocument.model_validate_json(path.read_text(encoding="utf-8"))
    by_attr: dict[str, PredictionSlot] = {}
    for item in document.extractions:
        attr_id = item.attribute_id
        if attr_id in by_attr:
            raise ValueError(f"Duplicate prediction for eos_id={eos_id}, attr_id={attr_id}")
        by_attr[attr_id] = PredictionSlot(
            eos_id=eos_id,
            attr_id=attr_id,
            value=None if item.error else item.value,
            unit=item.unit,
            raw_quote=item.raw_quote,
            source_section_id=item.source_section_id,
            top_rerank_section_id=item.top_rerank_section_id,
            rerank_score=item.rerank_score,
            high_confidence=item.high_confidence,
            error=item.error,
        )
    return by_attr


def load_predictions_for_universe(source_dir: Path, eos_ids: list[int]) -> dict[int, dict[str, PredictionSlot]]:
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Extraction eval source must be a directory: {source_dir}")
    predictions: dict[int, dict[str, PredictionSlot]] = {}
    for eos_id in eos_ids:
        path = source_dir / f"{eos_id}_extraction.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing extraction output: {path}")
        predictions[eos_id] = load_prediction_document(path, eos_id)
    return predictions
