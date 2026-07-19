from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import numpy as np

from infra.config import get_config_and_env
from infra.llm.callbacks import CompletionProgressCallback
from infra.llm.openai import get_openai_llm
from infra.llm_observability.langfuse import get_langfuse_handler
from research.steps.attribute_grouping.domain.embeddings import (
    build_embedding_text,
    cosine_similarity_matrix,
    embed_texts,
)
from research.steps.attribute_grouping.domain.llm_split import split_partition
from research.steps.attribute_grouping.domain.models import (
    AttributeGroup,
    AttributeGroups,
    ClassAttributeSet,
)
from research.steps.attribute_grouping.domain.partition import (
    build_tight_groups_and_remainder,
    compute_partition_sizes,
    partition_into_balanced_partitions,
)


def run_grouping(attr_set: ClassAttributeSet) -> AttributeGroups:
    config = get_config_and_env()
    ag = config["ATTRIBUTE_GROUPING"]
    min_group_size = int(ag["min_group_size"])
    max_group_size = int(ag["max_group_size"])
    tight_sim_threshold = float(ag["tight_sim_threshold"])
    max_partition_size = int(ag["max_partition_size"])
    llm_model_key: str = ag["llm_model_key"]
    embedder_model_key: str = ag["embedder_model_key"]
    max_concurrent_requests = int(ag["max_concurrent_requests"])

    all_attr_ids = sorted(attr_set.attributes.keys())

    if not all_attr_ids:
        return AttributeGroups(groups=[])

    llm = get_openai_llm(llm_model_key, config)
    langfuse_handler = get_langfuse_handler()

    texts = [build_embedding_text(attr_set.attributes[aid]) for aid in all_attr_ids]
    emb = embed_texts(texts, embedder_model_key, config)
    sim = cosine_similarity_matrix(emb)
    np.fill_diagonal(sim, 1.0)

    tight_groups, remainder_idx = build_tight_groups_and_remainder(
        sim,
        all_attr_ids,
        tight_sim_threshold=tight_sim_threshold,
        min_group_size=min_group_size,
        max_group_size=max_group_size,
    )

    rem = sorted(remainder_idx)
    llm_partitions: list[list[str]] = []
    if rem:
        rem_sim = sim[np.ix_(rem, rem)]
        rem_ids = [all_attr_ids[i] for i in rem]
        part_sizes = compute_partition_sizes(len(rem), max_partition_size=max_partition_size)
        llm_partitions = partition_into_balanced_partitions(rem_sim, rem_ids, part_sizes)

    with CompletionProgressCallback(total=len(llm_partitions), desc="Grouping") as progress:
        callbacks = [h for h in [langfuse_handler, progress] if h is not None]

        def _split_one(partition: list[str]) -> list[list[str]]:
            return split_partition(
                partition,
                attr_set.attributes,
                llm,
                callbacks,
                min_group_size=min_group_size,
                max_group_size=max_group_size,
            )

        with ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
            llm_results = list(executor.map(_split_one, llm_partitions))

    groups_out: list[list[str]] = list(tight_groups)
    for partition, multi_groups in zip(llm_partitions, llm_results):
        in_multi = {aid for g in multi_groups for aid in g}
        groups_out.extend(multi_groups)
        for aid in sorted(set(partition) - in_multi):
            groups_out.append([aid])

    covered: set[str] = set()
    final: list[list[str]] = []
    for g in groups_out:
        new_ids = [a for a in g if a not in covered]
        covered.update(new_ids)
        if new_ids:
            final.append(new_ids)
    for aid in all_attr_ids:
        if aid not in covered:
            final.append([aid])
            covered.add(aid)

    return AttributeGroups(groups=[AttributeGroup(attr_ids=g) for g in final])
