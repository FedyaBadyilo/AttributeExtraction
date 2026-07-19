"""Tests for context rebuild after context grouping."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from research.steps.attribute_grouping.domain.models import AttributeGroup, AttributeGroups
from research.steps.context_rebuild.domain.runner import rebuild_grouped_context
from research.steps.extraction.domain.prompts import _format_context
from research.steps.merge.domain.context_merge import MergedChunkRow
from research.steps.merge.domain.models import MergedChunk, MergeResult
from research.steps.reranking.domain.models import RerankAttribute, RerankChunk

_PATCH_BUILD = "research.steps.context_rebuild.domain.runner.build_merged_section"


def _merged_chunk(
    *,
    section_id: int,
    source_point_ids: list[int],
) -> MergedChunk:
    return MergedChunk(
        source_point_ids=source_point_ids,
        display_point_id=section_id,
        content=f"old-{section_id}",
        header_path=["Old"],
        section_id=section_id,
    )


def _rerank_chunk(
    *,
    section_id: int,
    source_point_ids: list[int],
    score: float = 0.9,
) -> RerankChunk:
    return RerankChunk(
        source_point_ids=source_point_ids,
        display_point_id=section_id,
        content=f"old-{section_id}",
        header_path=["Old"],
        section_id=section_id,
        rerank_score=score,
    )


def test_rebuild_grouped_context_unions_table_point_ids() -> None:
    section_id = 10
    attr_groups = AttributeGroups(groups=[AttributeGroup(attr_ids=["a1", "a2"])])
    rerank_result = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[_rerank_chunk(section_id=section_id, source_point_ids=[section_id, 1, 2])],
        ),
        RerankAttribute(
            attribute_id="a2",
            rerank_chunks=[_rerank_chunk(section_id=section_id, source_point_ids=[section_id, 2, 3])],
        ),
    ]
    merge_results = [
        MergeResult(
            attribute_id="a1",
            merged_chunks=[_merged_chunk(section_id=section_id, source_point_ids=[section_id, 1, 2])],
        ),
        MergeResult(
            attribute_id="a2",
            merged_chunks=[_merged_chunk(section_id=section_id, source_point_ids=[section_id, 2, 3])],
        ),
    ]

    def _fake_build(sec_id: int, table_ids: list[int], qdrant, collection_name, **kwargs) -> MergedChunkRow:
        assert sec_id == section_id
        assert set(table_ids) == {1, 2, 3}
        assert kwargs == {"expansion_char_budget": None}
        return MergedChunkRow(
            display_point_id=section_id,
            merged_text="rebuilt-content",
            header_path=["New"],
            source_point_ids=sorted([section_id, *table_ids]),
            section_id=section_id,
        )

    with patch(_PATCH_BUILD, side_effect=_fake_build):
        result = rebuild_grouped_context(attr_groups, rerank_result, merge_results, MagicMock(), "col")

    assert len(result.groups) == 1
    assert len(result.groups[0].grouped_chunks) == 1
    rebuilt = result.groups[0].grouped_chunks[0]
    assert rebuilt.content == "rebuilt-content"
    assert rebuilt.header_path == ["New"]
    assert set(rebuilt.source_point_ids) == {section_id, 1, 2, 3}


def test_rebuild_grouped_context_does_not_emit_rerank_score() -> None:
    section_id = 10
    attr_groups = AttributeGroups(groups=[AttributeGroup(attr_ids=["a1"])])
    rerank_result = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[_rerank_chunk(section_id=section_id, source_point_ids=[section_id, 1])],
        )
    ]
    merge_results = [
        MergeResult(
            attribute_id="a1",
            merged_chunks=[_merged_chunk(section_id=section_id, source_point_ids=[section_id, 1])],
        )
    ]

    with patch(
        _PATCH_BUILD,
        return_value=MergedChunkRow(
            display_point_id=section_id,
            merged_text="new",
            header_path=[],
            source_point_ids=[section_id, 1],
            section_id=section_id,
        ),
    ):
        result = rebuild_grouped_context(attr_groups, rerank_result, merge_results, MagicMock(), "col")

    assert "rerank_score" not in result.groups[0].grouped_chunks[0].model_dump()
    assert result.rerank_result == rerank_result


def test_rebuild_grouped_context_removes_attachment_placeholders() -> None:
    section_id = 10
    attr_groups = AttributeGroups(groups=[AttributeGroup(attr_ids=["a1"])])
    rerank_result = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[_rerank_chunk(section_id=section_id, source_point_ids=[section_id])],
        )
    ]
    merge_results = [
        MergeResult(
            attribute_id="a1",
            merged_chunks=[_merged_chunk(section_id=section_id, source_point_ids=[section_id])],
        )
    ]

    with patch(
        _PATCH_BUILD,
        return_value=MergedChunkRow(
            display_point_id=section_id,
            merged_text="before\n<attachment attach_123>\n\nafter",
            header_path=[],
            source_point_ids=[section_id],
            section_id=section_id,
        ),
    ):
        result = rebuild_grouped_context(attr_groups, rerank_result, merge_results, MagicMock(), "col")

    rebuilt = result.groups[0].grouped_chunks[0]
    assert rebuilt.content == "beforeafter"
    assert "<attachment" not in rebuilt.content


def test_rebuild_grouped_context_fails_on_missing_merge_join() -> None:
    attr_groups = AttributeGroups(groups=[AttributeGroup(attr_ids=["a1"])])
    rerank_result = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[_rerank_chunk(section_id=10, source_point_ids=[10, 1])],
        )
    ]

    with pytest.raises(ValueError, match="Missing merge chunk"):
        rebuild_grouped_context(attr_groups, rerank_result, [], MagicMock(), "col")


def test_rebuild_grouped_context_fails_on_missing_rerank_attribute() -> None:
    attr_groups = AttributeGroups(groups=[AttributeGroup(attr_ids=["a1"])])

    with pytest.raises(ValueError, match="Missing rerank result"):
        rebuild_grouped_context(attr_groups, [], [], MagicMock(), "col")


def test_extraction_context_removes_internal_placeholders() -> None:
    chunk = MergedChunk(
        source_point_ids=[1],
        display_point_id=1,
        content=(
            "before\n<attachment attach_123>\n\n"
            'middle\n<table_ref uid="table_456"/>\n\n'
            "after"
        ),
        header_path=["Section"],
        section_id=1,
    )

    context = _format_context([chunk], priority_by_point_id={1: 2})

    assert "<attachment" not in context
    assert "table_ref" not in context
    assert "beforemiddleafter" in context
