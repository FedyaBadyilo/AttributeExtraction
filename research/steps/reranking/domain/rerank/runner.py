"""
Rerank layer: LLM relevance scoring on merged chunks per attribute.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from infra.llm.callbacks import CompletionProgressCallback
from infra.llm.openai import get_openai_llm
from infra.llm_observability.langfuse import get_langfuse_handler
from research.steps.attribute_grouping.domain.models import ClassAttributeSet
from research.steps.merge.domain.models import MergedChunk, MergeResult
from research.steps.reranking.domain.models import RerankAttribute, RerankChunk
from research.steps.reranking.domain.rerank.prompts import build_system_prompt, build_user_prompt
from research.steps.reranking.domain.rerank.schemas import (
    build_attribute_rerank_response_model,
    chunk_numbers_to_source_point_ids,
)

logger = logging.getLogger(__name__)
ChunkKey = tuple[int, ...]


def _merged_chunks_in_prompt_order(
    chunk_keys: list[ChunkKey],
    merged_chunks_by_key: dict[ChunkKey, MergedChunk],
) -> list[MergedChunk]:
    """Те же merged chunks и порядок, что уходят в build_user_prompt."""
    return [
        merged_chunks_by_key[chunk_key]
        for chunk_key in chunk_keys
        if chunk_key in merged_chunks_by_key
    ]


def _index_merged_chunks_by_source_ids(merge_results: list[MergeResult]) -> dict[ChunkKey, MergedChunk]:
    """Словарь source_point_ids → MergedChunk по всем атрибутам."""
    merged_chunks_by_key: dict[ChunkKey, MergedChunk] = {}
    for r in merge_results:
        for m in r.merged_chunks:
            merged_chunks_by_key[m.source_point_ids] = m
    return merged_chunks_by_key


def rerank_merged_contexts(
    merge_results: list[MergeResult],
    attr_set: ClassAttributeSet,
    config: dict[str, Any],
    *,
    priority_by_point_id: dict[int, int],
    execution_variant: str | None = None,
) -> list[RerankAttribute]:
    """
    LLM rerank per attribute, truncate to top_k; on failure — pre-rerank order truncated to fallback_top_k.
    Использует из входа merge только `attribute_id` и `merged_chunks`.
    Возвращает по одному `RerankAttribute` на атрибут с `RerankChunk` и скорами.
    """
    rerank_cfg = config["RERANKING"]["rerank"]
    model_key = str(rerank_cfg["llm_model_key"])
    top_k = int(rerank_cfg["top_k"])
    fallback_top_k = int(rerank_cfg["fallback_top_k"])
    if fallback_top_k <= top_k:
        raise ValueError(
            "RERANKING.rerank.fallback_top_k must be greater than RERANKING.rerank.top_k "
            f"(got fallback_top_k={fallback_top_k}, top_k={top_k})."
        )
    max_concurrent = int(rerank_cfg["max_concurrent_requests"])
    llm = get_openai_llm(model_key, config)

    langfuse_handler = get_langfuse_handler()

    merged_chunks_by_key = _index_merged_chunks_by_source_ids(merge_results)
    active = attr_set.attributes

    new_order: dict[str, list[ChunkKey]] = {}
    rerank_scores: dict[str, dict[ChunkKey, float]] = {}

    attr_items = [(r.attribute_id, [m.source_point_ids for m in r.merged_chunks]) for r in merge_results]
    pending_items: list[tuple[str, list[ChunkKey]]] = []
    for aid, chunk_keys in attr_items:
        if not chunk_keys:
            new_order[aid] = []
            rerank_scores[aid] = {}
        else:
            pending_items.append((aid, chunk_keys))

    def _apply_rerank_fallback(aid: str, chunk_keys: list[ChunkKey]) -> None:
        new_order[aid] = chunk_keys[:fallback_top_k]
        rerank_scores[aid] = {
            chunk_key: 0.0 for chunk_key in chunk_keys
        }

    def _run_one(task: dict[str, Any]) -> tuple[str, list[ChunkKey], Any]:
        try:
            bound = llm.with_structured_output(
                task["response_model"],
                include_raw=True,
                method="function_calling",
            )
            resp = bound.invoke(task["messages"], **task["invoke_config"])
            return task["aid"], task["chunk_keys"], resp
        except Exception as e:
            logger.warning("Rerank fallback for %s: %s", task["aid"], e)
            return task["aid"], task["chunk_keys"], {"fallback_pre_rerank_order": True}

    with CompletionProgressCallback(
        len(pending_items),
        desc="Rerank",
        unit="attr",
    ) as progress_cb:
        tasks: list[dict[str, Any]] = []
        for aid, chunk_keys in pending_items:
            attr = active[aid]
            chunks = _merged_chunks_in_prompt_order(chunk_keys, merged_chunks_by_key)

            user_prompt = build_user_prompt(
                attr_name=attr.attr_name,
                value_type=str(attr.attr_type.value),
                unit_enum_list=attr.units,
                chunks=chunks,
                execution_variant=execution_variant,
                extraction_hint=attr.descr,
                priority_by_point_id=priority_by_point_id,
            )
            system_prompt = build_system_prompt(
                include_extraction_hint=bool(attr.descr),
                include_execution_variant=bool(execution_variant),
            )
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

            run_name = f"rerank[{attr.attr_name}]"
            invoke_callbacks: list[Any] = []
            if langfuse_handler:
                invoke_callbacks.append(langfuse_handler)
            invoke_callbacks.append(progress_cb)
            invoke_config: dict[str, Any] = {
                "config": {"callbacks": invoke_callbacks, "run_name": run_name},
            }
            response_model = build_attribute_rerank_response_model(len(chunks))
            tasks.append(
                {
                    "aid": aid,
                    "chunk_keys": chunk_keys,
                    "response_model": response_model,
                    "messages": messages,
                    "invoke_config": invoke_config,
                }
            )

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            task_results = list(executor.map(_run_one, tasks))

    for aid, chunk_keys, resp in task_results:
        if isinstance(resp, dict) and resp.get("fallback_pre_rerank_order"):
            _apply_rerank_fallback(aid, chunk_keys)
            continue

        try:
            if isinstance(resp, dict):
                raw_msg = resp.get("raw")
                if raw_msg is not None:
                    _ = raw_msg.additional_kwargs.get("lc_reasoning")
                if resp.get("parsing_error") is not None or resp.get("parsed") is None:
                    raise ValueError(
                        f"Reranker structured parse failed for {aid}: {resp.get('parsing_error')}"
                    )
                parsed = resp["parsed"]
            else:
                parsed = resp

            chunks_for_attr = _merged_chunks_in_prompt_order(chunk_keys, merged_chunks_by_key)
            chunk_no_to_source_ids = chunk_numbers_to_source_point_ids(chunks_for_attr)
            scored_map: dict[ChunkKey, float] = {
                chunk_no_to_source_ids[it.chunk_number]: it.relevance_score for it in parsed.scores
            }
            missing_keys = [
                chunk_key
                for chunk_key in chunk_keys
                if chunk_key not in scored_map
            ]
            if missing_keys:
                raise ValueError(
                    f"Reranker returned incomplete scores for {aid}, missing: {missing_keys}"
                )

            pos = {
                chunk_key: i
                for i, chunk_key in enumerate(chunk_keys)
            }
            ordered = sorted(
                chunk_keys,
                key=lambda chunk_key: (
                    -scored_map[chunk_key],
                    pos[chunk_key],
                ),
            )
            ordered = ordered[: max(top_k, 0)]

            new_order[aid] = ordered
            rerank_scores[aid] = {
                chunk_key: scored_map[chunk_key]
                for chunk_key in chunk_keys
            }
        except Exception as e:
            logger.warning(
                "Rerank fallback for %s: %s. Using pre-rerank merge order truncated to fallback_top_k=%d.",
                aid,
                e,
                fallback_top_k,
            )
            _apply_rerank_fallback(aid, chunk_keys)

    out: list[RerankAttribute] = []
    for r in merge_results:
        aid = r.attribute_id
        ordered_keys = new_order.get(aid, [m.source_point_ids for m in r.merged_chunks])
        scores_for_aid = rerank_scores.get(aid, {})
        rcs: list[RerankChunk] = []
        for chunk_key in ordered_keys:
            if chunk_key not in merged_chunks_by_key:
                continue
            m = merged_chunks_by_key[chunk_key]
            sc = float(scores_for_aid.get(chunk_key, 0.0))
            rcs.append(RerankChunk(**m.model_dump(), rerank_score=sc))
        out.append(RerankAttribute(attribute_id=aid, rerank_chunks=rcs))

    return out
