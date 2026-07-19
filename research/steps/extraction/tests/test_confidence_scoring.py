from __future__ import annotations

from research.steps.extraction.domain.runner import (
    _best_rerank_chunks_by_section,
    _resolve_cited_section_score,
)
from research.steps.reranking.domain.models import RerankChunk


def _rerank_chunk(
    label: str,
    *,
    section_id: int,
    score: float,
) -> RerankChunk:
    return RerankChunk(
        source_point_ids=[section_id],
        display_point_id=section_id,
        content=f"content-{label}",
        header_path=[],
        section_id=section_id,
        rerank_score=score,
    )


def test_best_rerank_chunks_by_section_keeps_highest_score() -> None:
    result = _best_rerank_chunks_by_section(
        [
            _rerank_chunk("low", section_id=10, score=0.1),
            _rerank_chunk("high", section_id=10, score=0.8),
        ]
    )

    assert result[10].content == "content-high"
    assert result[10].rerank_score == 0.8


def test_resolve_cited_section_score_matches_by_section() -> None:
    score_index = {"attr1": {10: 0.8}}

    score, section_id = _resolve_cited_section_score(
        "attr1",
        10,
        score_index,
    )

    assert score == 0.8
    assert section_id == 10


def test_resolve_cited_section_score_missing_section_returns_zero() -> None:
    score, section_id = _resolve_cited_section_score(
        "attr1",
        None,
        {"attr1": {10: 0.8}},
    )

    assert score == 0.0
    assert section_id is None
