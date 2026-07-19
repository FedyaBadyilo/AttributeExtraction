from __future__ import annotations

import numpy as np
import pytest

from research.steps.attribute_grouping.domain.partition import (
    build_tight_groups_and_remainder,
    compute_partition_sizes,
    partition_into_balanced_partitions,
)


def test_compute_partition_sizes_empty() -> None:
    assert compute_partition_sizes(0, max_partition_size=5) == []


def test_compute_partition_sizes_single() -> None:
    assert compute_partition_sizes(1, max_partition_size=5) == [1]


def test_compute_partition_sizes_ten() -> None:
    sizes = compute_partition_sizes(10, max_partition_size=3)
    assert sum(sizes) == 10
    assert all(s <= 3 for s in sizes)


def test_partition_into_balanced_shape_mismatch_raises() -> None:
    sim = np.eye(3)
    with pytest.raises(ValueError):
        partition_into_balanced_partitions(sim, ["a", "b"], [2])


def test_partition_into_balanced_small() -> None:
    sim = np.eye(3)
    ids = ["a", "b", "c"]
    partitions = partition_into_balanced_partitions(sim, ids, [2, 1])
    flat = [aid for p in partitions for aid in p]
    assert sorted(flat) == sorted(ids)
    assert len(partitions) == 2


def test_build_tight_groups_high_similarity_pair() -> None:
    sim = np.array(
        [
            [1.0, 0.95, 0.1],
            [0.95, 1.0, 0.1],
            [0.1, 0.1, 1.0],
        ]
    )
    ids = ["a", "b", "c"]
    tight_groups, remainder_idx = build_tight_groups_and_remainder(
        sim, ids, tight_sim_threshold=0.9, min_group_size=2, max_group_size=5
    )
    all_tight = [aid for g in tight_groups for aid in g]
    assert "a" in all_tight and "b" in all_tight
    assert sorted(["a", "b"]) in [sorted(g) for g in tight_groups]
    assert 2 in remainder_idx
