from __future__ import annotations

from research.steps.attribute_grouping.domain.llm_split import _merge_non_overlapping_groups


def test_merge_non_overlapping_groups_removes_overlaps() -> None:
    groups = [["a", "b"], ["b", "c"]]
    result = _merge_non_overlapping_groups(groups, min_group_size=2, max_group_size=5)
    assert result == [["a", "b"]]


def test_merge_non_overlapping_groups_filters_too_small() -> None:
    groups = [["a"], ["b", "c"], ["e", "f"]]
    result = _merge_non_overlapping_groups(groups, min_group_size=2, max_group_size=5)
    assert ["a"] not in result
    assert ["b", "c"] in result
    assert ["e", "f"] in result


def test_merge_non_overlapping_groups_filters_too_large() -> None:
    groups = [["a", "b", "c", "d", "e", "f"]]
    result = _merge_non_overlapping_groups(groups, min_group_size=2, max_group_size=5)
    assert result == []
