from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from research.steps.attribute_grouping.domain.models import (
    AttrType,
    ClassAttribute,
    ClassAttributeSet,
)
from research.steps.merge.domain.models import MergedChunk, MergeResult
from research.steps.reranking.domain.rerank.runner import rerank_merged_contexts


def _config() -> dict[str, Any]:
    return {
        "RERANKING": {
            "rerank": {
                "llm_model_key": "rerank_llm",
                "top_k": 2,
                "fallback_top_k": 5,
                "max_concurrent_requests": 2,
            },
        },
    }


def _attr_set(attr_id: str = "attr1") -> ClassAttributeSet:
    return ClassAttributeSet(
        class_code="TEST",
        attributes={
            attr_id: ClassAttribute(
                attr_id=attr_id,
                attr_name="Test Attribute",
                descr=None,
                attr_type=AttrType.STRING,
                for_extraction=True,
                units=None,
                allowed_values=None,
            ),
        },
    )


def _merged_chunk(label: str, display_point_id: int | None = None) -> MergedChunk:
    dp = display_point_id
    if dp is None:
        dp = int(label[1:]) if label.startswith("c") and label[1:].isdigit() else 1
    return MergedChunk(
        source_point_ids=[dp],
        display_point_id=dp,
        content=f"content-{label}",
        header_path=["Section"],
        section_id=dp,
    )


def _merge_result(
    attr_id: str,
    merged_chunks: list[MergedChunk],
) -> MergeResult:
    return MergeResult(attribute_id=attr_id, merged_chunks=merged_chunks)


@patch("research.steps.reranking.domain.rerank.runner.get_langfuse_handler", return_value=None)
@patch("research.steps.reranking.domain.rerank.runner.get_openai_llm")
def test_empty_merged_chunks_returns_empty_order(
    mock_get_llm: MagicMock,
    _mock_langfuse: MagicMock,
) -> None:
    mock_llm = MagicMock()
    mock_get_llm.return_value = mock_llm

    results = rerank_merged_contexts(
        [_merge_result("attr1", [])],
        _attr_set(),
        _config(),
        priority_by_point_id={},
    )
    assert len(results) == 1
    assert results[0].attribute_id == "attr1"
    assert results[0].rerank_chunks == []
    mock_llm.with_structured_output.assert_not_called()


@patch("research.steps.reranking.domain.rerank.runner.get_langfuse_handler", return_value=None)
@patch("research.steps.reranking.domain.rerank.runner.get_openai_llm")
def test_worker_exception_uses_fallback_top_k(
    mock_get_llm: MagicMock,
    _mock_langfuse: MagicMock,
) -> None:
    mock_llm = MagicMock()
    mock_bound = MagicMock()
    mock_bound.invoke.side_effect = RuntimeError("LLM down")
    mock_llm.with_structured_output.return_value = mock_bound
    mock_get_llm.return_value = mock_llm

    chunks = [_merged_chunk(f"c{i}") for i in range(1, 8)]
    results = rerank_merged_contexts(
        [_merge_result("attr1", chunks)],
        _attr_set(),
        _config(),
        priority_by_point_id={},
    )
    assert len(results[0].rerank_chunks) == 5
    assert [rc.content for rc in results[0].rerank_chunks] == [f"content-c{i}" for i in range(1, 6)]
    assert all(rc.rerank_score == 0.0 for rc in results[0].rerank_chunks)


@patch("research.steps.reranking.domain.rerank.runner.get_langfuse_handler", return_value=None)
@patch("research.steps.reranking.domain.rerank.runner.get_openai_llm")
def test_rerank_sorts_by_score_desc_then_truncates_top_k(
    mock_get_llm: MagicMock,
    _mock_langfuse: MagicMock,
) -> None:
    response_model = None

    def _capture_model(model: type, **kwargs: Any) -> MagicMock:
        nonlocal response_model
        response_model = model
        mock_bound = MagicMock()

        def _invoke(_messages: list, **invoke_kwargs: Any) -> dict[str, Any]:
            assert response_model is not None
            parsed = response_model.model_validate(
                {
                    "scores": [
                        {"chunk_number": 1, "relevance_score": 0.3},
                        {"chunk_number": 2, "relevance_score": 0.9},
                        {"chunk_number": 3, "relevance_score": 0.6},
                    ]
                }
            )
            return {"parsed": parsed, "parsing_error": None, "raw": None}

        mock_bound.invoke.side_effect = _invoke
        return mock_bound

    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = _capture_model
    mock_get_llm.return_value = mock_llm

    chunks = [_merged_chunk("c1"), _merged_chunk("c2"), _merged_chunk("c3")]
    results = rerank_merged_contexts(
        [_merge_result("attr1", chunks)],
        _attr_set(),
        _config(),
        priority_by_point_id={},
    )
    ordered = results[0].rerank_chunks
    assert [rc.content for rc in ordered] == ["content-c2", "content-c3"]
    assert ordered[0].rerank_score == pytest.approx(0.9)
    assert ordered[1].rerank_score == pytest.approx(0.6)
