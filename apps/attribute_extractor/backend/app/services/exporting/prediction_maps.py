from __future__ import annotations

from typing import TYPE_CHECKING, Any

from backend.app.pipeline.runner import PipelineTzResult
from backend.app.schemas import TzPackageRead
from backend.app.services.exporting.common import is_missing, package_key, package_recpart

if TYPE_CHECKING:
    from research.steps.extraction.domain.models import ExtractedAttributeItem


def prediction_maps(
    packages: list[TzPackageRead],
    result_by_package: dict[str, PipelineTzResult],
) -> tuple[
    dict[tuple[str, str], Any],
    dict[tuple[str, str], str | None],
    dict[tuple[str, str], bool | None],
    dict[tuple[str, str], str | None],
    frozenset[tuple[str, str]],
]:
    value_map: dict[tuple[str, str], Any] = {}
    unit_map: dict[tuple[str, str], str | None] = {}
    high_confidence_map: dict[tuple[str, str], bool | None] = {}
    source_text_map: dict[tuple[str, str], str | None] = {}
    error_keys: set[tuple[str, str]] = set()

    for package in packages:
        result = result_by_package.get(package_key(package))
        if result is None:
            continue
        recpart = package_recpart(package)
        source_chunks = result.source_chunks_by_attribute or {}
        for ext in result.extractions.extractions:
            key = (recpart, ext.attribute_id)
            if ext.error:
                value_map[key] = None
                unit_map[key] = None
                high_confidence_map[key] = None
                source_text_map[key] = None
                error_keys.add(key)
                continue
            value_map[key] = ext.value
            unit_map[key] = ext.unit
            high_confidence_map[key] = ext.high_confidence
            source_text_map[key] = source_text_for_extraction(source_chunks, ext)
    return value_map, unit_map, high_confidence_map, source_text_map, frozenset(error_keys)


def source_chunk_text(
    source_chunks: dict[str, dict[int, str]],
    attribute_id: str,
    source_chunk_id: int | None,
) -> str | None:
    if source_chunk_id is None:
        return None
    return source_chunks.get(attribute_id, {}).get(int(source_chunk_id))


def source_text_for_extraction(
    source_chunks: dict[str, dict[int, str]],
    ext: "ExtractedAttributeItem",
) -> str | None:
    section_id = ext.source_section_id
    if section_id is None and is_missing(ext.value):
        section_id = ext.top_rerank_section_id
    return source_chunk_text(source_chunks, ext.attribute_id, section_id)


def prediction_maps_for_eval(
    packages: list[TzPackageRead],
    result_by_package: dict[str, PipelineTzResult],
) -> tuple[
    dict[tuple[str, str], Any],
    dict[tuple[str, str], str | None],
    dict[tuple[str, str], bool | None],
    dict[tuple[str, str], str | None],
    frozenset[tuple[str, str]],
]:
    value_map, unit_map, high_confidence_map, _, error_keys = prediction_maps(packages, result_by_package)
    raw_quote_map: dict[tuple[str, str], str | None] = {}
    for package in packages:
        result = result_by_package.get(package_key(package))
        if result is None:
            continue
        recpart = package_recpart(package)
        for ext in result.extractions.extractions:
            raw_quote_map[(recpart, ext.attribute_id)] = None if ext.error else ext.raw_quote
    return value_map, unit_map, high_confidence_map, raw_quote_map, error_keys


def fill_missing_eval_cases(
    *,
    eval_cases: list[tuple[str, str]],
    gt_value_map: dict[tuple[str, str], Any],
    pred_value_map: dict[tuple[str, str], Any],
    gt_unit_map: dict[tuple[str, str], str | None],
    pred_unit_map: dict[tuple[str, str], str | None],
    high_confidence_map: dict[tuple[str, str], bool | None],
    raw_quote_map: dict[tuple[str, str], str | None],
) -> None:
    for key in eval_cases:
        gt_value_map.setdefault(key, None)
        pred_value_map.setdefault(key, None)
        gt_unit_map.setdefault(key, None)
        pred_unit_map.setdefault(key, None)
        high_confidence_map.setdefault(key, None)
        raw_quote_map.setdefault(key, None)
