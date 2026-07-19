from __future__ import annotations

import math
from collections import defaultdict

import numpy as np
from scipy.cluster import hierarchy
from scipy.spatial.distance import squareform


def _uf_find(parent: list[int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _uf_union(parent: list[int], a: int, b: int) -> None:
    ra, rb = _uf_find(parent, a), _uf_find(parent, b)
    if ra != rb:
        parent[rb] = ra


def compute_partition_sizes(n: int, *, max_partition_size: int) -> list[int]:
    if n <= 0:
        return []
    part = min(n, max_partition_size)
    k = math.ceil(n / part)
    base = n // k
    extra = n % k
    return [base + 1 if i < extra else base for i in range(k)]


def partition_into_balanced_partitions(
    similarity_matrix: np.ndarray,
    attr_ids: list[str],
    partition_sizes: list[int],
) -> list[list[str]]:
    n = len(attr_ids)
    k = len(partition_sizes)
    if similarity_matrix.shape != (n, n):
        raise ValueError(
            f"similarity_matrix shape {similarity_matrix.shape} does not match n={n}"
        )
    if sum(partition_sizes) != n:
        raise ValueError(f"partition_sizes sum {sum(partition_sizes)} != n={n}")

    if n == 1:
        return [[attr_ids[0]]]
    if k == 1:
        return [list(attr_ids)]

    dist = 1.0 - similarity_matrix
    np.fill_diagonal(dist, 0.0)
    condensed = squareform(dist, checks=False)
    z = hierarchy.linkage(condensed, method="average")
    labels = hierarchy.fcluster(z, t=k, criterion="maxclust")

    clusters: list[list[int]] = [[] for _ in range(k)]
    for i in range(n):
        c = int(labels[i]) - 1
        if c >= k:
            c = k - 1
        clusters[c].append(i)

    target = list(partition_sizes)
    for _ in range(n * k):
        sizes = [len(c) for c in clusters]
        if sizes == target:
            break
        over = [b for b in range(k) if sizes[b] > target[b]]
        under = [b for b in range(k) if sizes[b] < target[b]]
        if not over or not under:
            break
        from_b, to_b = over[0], under[0]
        best_idx = clusters[from_b][0]
        best_sum = float("inf")
        for idx in clusters[from_b]:
            s = sum(similarity_matrix[idx, j] for j in clusters[from_b] if j != idx)
            if s < best_sum:
                best_sum = s
                best_idx = idx
        clusters[from_b].remove(best_idx)
        clusters[to_b].append(best_idx)

    return [[attr_ids[i] for i in c] for c in clusters]


def build_tight_groups_and_remainder(
    sim: np.ndarray,
    attr_ids: list[str],
    *,
    tight_sim_threshold: float,
    min_group_size: int,
    max_group_size: int,
) -> tuple[list[list[str]], set[int]]:
    n = len(attr_ids)
    aid_to_i = {attr_ids[i]: i for i in range(n)}
    parent = list(range(n))

    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] > tight_sim_threshold:
                _uf_union(parent, i, j)

    by_root: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        by_root[_uf_find(parent, i)].append(i)

    tight_groups_idx: list[list[int]] = []
    remainder_idx: set[int] = set()

    for idxs in by_root.values():
        idxs = sorted(idxs)
        sz = len(idxs)
        if sz == 1:
            remainder_idx.add(idxs[0])
            continue
        if sz <= max_group_size:
            if sz >= min_group_size:
                tight_groups_idx.append(idxs)
            else:
                remainder_idx.update(idxs)
            continue
        sub_sim = sim[np.ix_(idxs, idxs)]
        sub_attr_ids = [attr_ids[idxs[i]] for i in range(len(idxs))]
        part_sizes = compute_partition_sizes(len(idxs), max_partition_size=max_group_size)
        parts = partition_into_balanced_partitions(sub_sim, sub_attr_ids, part_sizes)
        for part in parts:
            gidx = [aid_to_i[a] for a in part]
            if len(gidx) >= min_group_size:
                tight_groups_idx.append(sorted(gidx))
            else:
                remainder_idx.update(gidx)

    tight_as_ids = [[attr_ids[i] for i in g] for g in tight_groups_idx]
    return tight_as_ids, remainder_idx
