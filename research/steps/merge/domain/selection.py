"""Char-budget selection of table splits for context merge expansion."""

from __future__ import annotations

from research.steps.merge.domain.table_stitch import IndexedSplit, _join_splits_with_header_dedup


def _merged_len_after_table_replace(merged: str, placeholder: str, table_content: str) -> int:
    return len(merged) - len(placeholder) + len(table_content)


def _select_expanded_table_splits(
    all_splits_indexed: list[IndexedSplit],
    selected: list[IndexedSplit],
    *,
    expansion_char_budget: int,
    merged: str,
    placeholder: str,
) -> list[IndexedSplit]:
    """Expand outward from each selected split while the merged chunk fits."""
    index_to_split = {s.table_chunk_index: s for s in all_splits_indexed}
    selected_indices = {s.table_chunk_index for s in selected}
    included_indices = set(selected_indices)

    def _fits(indices: set[int]) -> bool:
        splits = sorted([index_to_split[i] for i in indices], key=lambda x: x.table_chunk_index)
        table_content, _ = _join_splits_with_header_dedup(splits)
        return _merged_len_after_table_replace(merged, placeholder, table_content) <= expansion_char_budget

    min_idx = min(index_to_split)
    max_idx = max(index_to_split)

    for seed_idx in sorted(selected_indices):
        left = seed_idx - 1
        right = seed_idx + 1
        while left >= min_idx or right <= max_idx:
            added = False
            if left >= min_idx:
                if left in index_to_split and left not in included_indices:
                    trial = included_indices | {left}
                    if _fits(trial):
                        included_indices = trial
                        added = True
                left -= 1
            if right <= max_idx:
                if right in index_to_split and right not in included_indices:
                    trial = included_indices | {right}
                    if _fits(trial):
                        included_indices = trial
                        added = True
                right += 1
            if not added:
                break

    return sorted(
        [index_to_split[i] for i in included_indices],
        key=lambda x: x.table_chunk_index,
    )


def _select_optional_table_splits(
    all_splits_indexed: list[IndexedSplit],
    *,
    expansion_char_budget: int,
    merged: str,
    placeholder: str,
) -> list[IndexedSplit]:
    """Take optional table splits in table order while the merged chunk fits."""
    included: list[IndexedSplit] = []
    for split in all_splits_indexed:
        trial = [*included, split]
        table_content, _ = _join_splits_with_header_dedup(trial)
        if _merged_len_after_table_replace(merged, placeholder, table_content) > expansion_char_budget:
            break
        included = trial
    return included
