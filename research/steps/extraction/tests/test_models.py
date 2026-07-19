from __future__ import annotations

import pytest

from research.steps.extraction.domain.models import ExtractedAttributeItem, ExtractedAttributesDocument


def test_null_value_clears_source_chunk_and_unit() -> None:
    item = ExtractedAttributeItem(
        attribute_id="a1",
        value=None,
        unit="kg",
        source_section_id=1,
        top_rerank_section_id=2,
    )
    assert item.source_section_id is None
    assert item.unit is None
    assert item.top_rerank_section_id == 2


def test_set_value_clears_top_rerank_section_id() -> None:
    item = ExtractedAttributeItem(
        attribute_id="a1",
        value="X",
        source_section_id=1,
        top_rerank_section_id=2,
    )
    assert item.top_rerank_section_id is None
    assert item.source_section_id == 1


def test_requires_unit_rejects_null_unit_with_value() -> None:
    with pytest.raises(ValueError, match="unit is required"):
        ExtractedAttributeItem(
            attribute_id="a1",
            value=10,
            unit=None,
            requires_unit=True,
        )


def test_requires_unit_allows_value_with_unit() -> None:
    item = ExtractedAttributeItem(
        attribute_id="a1",
        value=10,
        unit="кг",
        requires_unit=True,
    )
    assert item.unit == "кг"
    assert "requires_unit" not in item.model_dump()


def test_error_item_serializes() -> None:
    item = ExtractedAttributeItem(
        attribute_id="a1",
        value=None,
        error=True,
        raw_quote="LLM failed",
    )
    data = item.model_dump()
    assert data["error"] is True
    assert data["raw_quote"] == "LLM failed"
    assert data["high_confidence"] is None


def test_empty_extractions_document_validates() -> None:
    doc = ExtractedAttributesDocument(extractions=[])
    assert doc.extractions == []
