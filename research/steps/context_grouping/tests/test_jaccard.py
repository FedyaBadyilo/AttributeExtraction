from __future__ import annotations

from research.steps.context_grouping.domain.jaccard import merge_groups_by_source_point_jaccard


def test_merge_groups_empty_plan() -> None:
    assert merge_groups_by_source_point_jaccard(
        [],
        {},
        merge_chunk_jaccard_min=0.5,
        max_group_size=5,
    ) == []


def test_merge_groups_high_jaccard_merges() -> None:
    attr_to_source_points = {
        "a": frozenset({1, 2}),
        "b": frozenset({1, 2, 3}),
    }
    plan = [["a"], ["b"]]
    merged = merge_groups_by_source_point_jaccard(
        plan,
        attr_to_source_points,
        merge_chunk_jaccard_min=0.5,
        max_group_size=5,
    )
    assert merged == [["a", "b"]]


def test_merge_groups_low_jaccard_no_merge() -> None:
    attr_to_source_points = {
        "a": frozenset({1}),
        "b": frozenset({2}),
    }
    plan = [["a"], ["b"]]
    merged = merge_groups_by_source_point_jaccard(
        plan,
        attr_to_source_points,
        merge_chunk_jaccard_min=0.5,
        max_group_size=5,
    )
    assert merged == [["a"], ["b"]]


def test_merge_groups_respects_max_group_size() -> None:
    attr_to_source_points = {
        "a": frozenset({1}),
        "b": frozenset({1}),
        "c": frozenset({1}),
        "d": frozenset({1}),
    }
    plan = [["a"], ["b"], ["c"], ["d"]]
    merged = merge_groups_by_source_point_jaccard(
        plan,
        attr_to_source_points,
        merge_chunk_jaccard_min=0.5,
        max_group_size=3,
    )
    assert all(len(g) <= 3 for g in merged)
    assert sorted(aid for g in merged for aid in g) == ["a", "b", "c", "d"]
