"""Hybrid Qdrant search: dense + client-side BM25 via RRF."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from infra.llm.embeddings import get_openai_embeddings
from infra.qdrant import get_qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.retrieval.domain.models import (
    AttributeSearchResult,
    ChunkHit,
    ChunkPayload,
)
from research.steps.retrieval.domain.query import build_search_query
from research.steps.vectorizing.domain.points import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME
from research.steps.vectorizing.domain.sparse_embed import embed_sparse_queries

logger = logging.getLogger(__name__)

EMBED_PARALLEL_WORKERS = 4


def _embed_dense_queries(texts: list[str], config: dict[str, Any]) -> list[list[float]]:
    if not texts:
        return []
    embedder_key: str = config["RETRIEVAL"]["embedder_model_key"]
    embedder = get_openai_embeddings(embedder_key, config)
    return embedder.embed_documents(texts, chunk_size=int(config["RETRIEVAL"]["embed_batch_size"]))


def _embed_hybrid_queries_parallel(
    texts: list[str],
    config: dict[str, Any],
) -> tuple[list[list[float]], list[qdrant_models.SparseVector]]:
    with ThreadPoolExecutor(max_workers=EMBED_PARALLEL_WORKERS) as pool:
        dense_future = pool.submit(_embed_dense_queries, texts, config)
        sparse_future = pool.submit(embed_sparse_queries, texts)
        return dense_future.result(), sparse_future.result()


def _make_hybrid_query_request(
    *,
    limit: int,
    prefetch_limit_dense: int,
    prefetch_limit_bm25: int,
    dense_vector: list[float],
    sparse_vector: qdrant_models.SparseVector,
) -> qdrant_models.QueryRequest:
    return qdrant_models.QueryRequest(
        prefetch=[
            qdrant_models.Prefetch(
                query=dense_vector,
                using=DENSE_VECTOR_NAME,
                limit=prefetch_limit_dense,
            ),
            qdrant_models.Prefetch(
                query=sparse_vector,
                using=SPARSE_VECTOR_NAME,
                limit=prefetch_limit_bm25,
            ),
        ],
        query=qdrant_models.FusionQuery(fusion=qdrant_models.Fusion.RRF),
        limit=limit,
        with_payload=True,
    )


def _hits_from_query_response(response: qdrant_models.QueryResponse, limit: int) -> list[ChunkHit]:
    hits: list[ChunkHit] = []
    for point in response.points:
        payload = ChunkPayload.model_validate(point.payload)
        hits.append(
            ChunkHit(
                id=int(point.id),
                score=point.score,
                payload=payload,
            )
        )
    hits.sort(key=lambda hit: -hit.score)
    return hits[:limit]


def _hybrid_search(
    qdrant: QdrantClient,
    collection_name: str,
    *,
    limit: int,
    prefetch_limit_dense: int,
    prefetch_limit_bm25: int,
    dense_vector: list[float],
    sparse_vector: qdrant_models.SparseVector,
) -> list[ChunkHit]:
    request = _make_hybrid_query_request(
        limit=limit,
        prefetch_limit_dense=prefetch_limit_dense,
        prefetch_limit_bm25=prefetch_limit_bm25,
        dense_vector=dense_vector,
        sparse_vector=sparse_vector,
    )
    responses = qdrant.query_batch_points(
        collection_name=collection_name,
        requests=[request],
    )
    return _hits_from_query_response(responses[0], limit)


def search_attributes(
    attrs_by_id: dict[str, ClassAttribute],
    collection_name: str,
    config: dict[str, Any],
    *,
    limit: int | None = None,
    prefetch_limit_dense: int | None = None,
    prefetch_limit_bm25: int | None = None,
    execution_variant: str | None = None,
    qdrant: QdrantClient | None = None,
) -> list[AttributeSearchResult]:
    """Hybrid vector search per attribute (dense + BM25 via Qdrant RRF)."""
    step_cfg = config["RETRIEVAL"]
    result_limit = limit if limit is not None else int(step_cfg["limit"])
    pf_dense = (
        prefetch_limit_dense
        if prefetch_limit_dense is not None
        else int(step_cfg["prefetch_limit_dense"])
    )
    pf_bm25 = (
        prefetch_limit_bm25
        if prefetch_limit_bm25 is not None
        else int(step_cfg["prefetch_limit_bm25"])
    )

    qdrant = qdrant or get_qdrant_client(config)
    results_by_id: dict[str, AttributeSearchResult] = {}

    searchable: list[tuple[str, str]] = []
    for attribute_id, attr in attrs_by_id.items():
        query_text = build_search_query(attr, execution_variant=execution_variant)
        if not query_text:
            results_by_id[attribute_id] = AttributeSearchResult(attribute_id=attribute_id, chunks=[])
            continue
        searchable.append((attribute_id, query_text))

    batch_attribute_ids: list[str] = []
    batch_requests: list[qdrant_models.QueryRequest] = []
    if searchable:
        query_texts = [query_text for _, query_text in searchable]
        dense_vectors, sparse_vectors = _embed_hybrid_queries_parallel(query_texts, config)
        for (attribute_id, _), dense_vector, sparse_vector in zip(
            searchable,
            dense_vectors,
            sparse_vectors,
            strict=True,
        ):
            batch_attribute_ids.append(attribute_id)
            batch_requests.append(
                _make_hybrid_query_request(
                    limit=result_limit,
                    prefetch_limit_dense=pf_dense,
                    prefetch_limit_bm25=pf_bm25,
                    dense_vector=dense_vector,
                    sparse_vector=sparse_vector,
                )
            )

    if batch_requests:
        responses = qdrant.query_batch_points(
            collection_name=collection_name,
            requests=batch_requests,
        )
        for attribute_id, response in zip(batch_attribute_ids, responses, strict=True):
            chunk_hits = _hits_from_query_response(response, result_limit)
            results_by_id[attribute_id] = AttributeSearchResult(
                attribute_id=attribute_id,
                chunks=chunk_hits,
            )
            logger.info("Attribute %s: %d chunks", attribute_id, len(chunk_hits))

    return [results_by_id[attribute_id] for attribute_id in attrs_by_id]
