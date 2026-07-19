"""Tests for context grouping from rerank evidence."""

from __future__ import annotations

from unittest.mock import MagicMock

from research.steps.attribute_grouping.domain.models import (
    AttributeGroup,
    AttributeGroups,
    ClassAttributeSet,
)
from research.steps.context_grouping.domain.runner import (
    attr_to_source_point_ids,
    build_context_attribute_groups,
)
from research.steps.reranking.domain.models import RerankAttribute, RerankChunk


def _rerank_chunk(
    chunk_id: str,
    score: float,
    source_ids: list[int],
    *,
    section_id: int | None = None,
) -> RerankChunk:
    parent_id = section_id if section_id is not None else source_ids[0]
    return RerankChunk(
        source_point_ids=source_ids,
        display_point_id=parent_id,
        content=f"content-{chunk_id}",
        header_path=[],
        rerank_score=score,
        section_id=parent_id,
    )


def _attr_set(attr_ids: list[str]) -> ClassAttributeSet:
    mock = MagicMock(spec=ClassAttributeSet)
    mock.attributes = {aid: MagicMock(attr_name=aid) for aid in attr_ids}
    return mock


def _attr_groups(groups: list[list[str]]) -> AttributeGroups:
    return AttributeGroups(groups=[AttributeGroup(attr_ids=g) for g in groups])


def _config(jaccard_min: float = 0.0, max_group_size: int = 10) -> dict:
    return {"RERANKING": {"grouping": {"merge_chunk_jaccard_min": jaccard_min, "max_group_size": max_group_size}}}


def test_attr_to_source_point_ids_union_across_blocks() -> None:
    rerank = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[
                _rerank_chunk("c1", 0.9, [10, 100, 101]),
                _rerank_chunk("c2", 0.5, [11, 110]),
            ],
        )
    ]

    result = attr_to_source_point_ids(rerank)

    assert result["a1"] == frozenset({10, 100, 101, 11, 110})


def test_attr_to_source_point_ids_two_attrs_overlapping() -> None:
    rerank = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[_rerank_chunk("c1", 0.9, [10, 100, 101])],
        ),
        RerankAttribute(
            attribute_id="a2",
            rerank_chunks=[_rerank_chunk("c2", 0.7, [10, 101, 102])],
        ),
    ]

    result = attr_to_source_point_ids(rerank)
    overlap = result["a1"] & result["a2"]

    assert 10 in overlap
    assert 101 in overlap


def test_context_grouping_outputs_attribute_groups_only() -> None:
    rerank = [
        RerankAttribute(
            attribute_id="a1",
            rerank_chunks=[_rerank_chunk("c1", 0.9, [10, 100])],
        ),
        RerankAttribute(
            attribute_id="a2",
            rerank_chunks=[_rerank_chunk("c2", 0.8, [10, 100])],
        ),
        RerankAttribute(
            attribute_id="a3",
            rerank_chunks=[_rerank_chunk("c3", 0.7, [90, 900])],
        ),
    ]

    result = build_context_attribute_groups(
        rerank,
        _attr_set(["a1", "a2", "a3"]),
        _config(jaccard_min=0.5),
        _attr_groups([["a1"], ["a2"], ["a3"]]),
    )

    assert isinstance(result, AttributeGroups)
    groups_by_attrs = {frozenset(g.attr_ids) for g in result.groups}
    assert frozenset({"a1", "a2"}) in groups_by_attrs
    assert frozenset({"a3"}) in groups_by_attrs


def test_context_grouping_keeps_attrs_with_no_rerank_chunks() -> None:
    rerank = [RerankAttribute(attribute_id="a1", rerank_chunks=[])]

    result = build_context_attribute_groups(
        rerank,
        _attr_set(["a1"]),
        _config(jaccard_min=0.5),
        _attr_groups([["a1"]]),
    )

    assert result == AttributeGroups(groups=[AttributeGroup(attr_ids=["a1"])])
