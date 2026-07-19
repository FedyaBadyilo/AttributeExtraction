"""Retrieval pipeline: hybrid search."""

from __future__ import annotations

from typing import Any

from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.retrieval.domain.models import AttributeSearchResult
from research.steps.retrieval.domain.search.runner import search_attributes


def run_retrieval(
    attrs_by_id: dict[str, ClassAttribute],
    collection_name: str,
    config: dict[str, Any],
    *,
    limit: int | None = None,
    prefetch_limit_dense: int | None = None,
    prefetch_limit_bm25: int | None = None,
    execution_variant: str | None = None,
) -> list[AttributeSearchResult]:
    return search_attributes(
        attrs_by_id=attrs_by_id,
        collection_name=collection_name,
        config=config,
        limit=limit,
        prefetch_limit_dense=prefetch_limit_dense,
        prefetch_limit_bm25=prefetch_limit_bm25,
        execution_variant=execution_variant,
    )
