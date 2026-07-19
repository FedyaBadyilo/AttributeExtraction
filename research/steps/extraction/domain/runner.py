from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from infra.llm.callbacks import CompletionProgressCallback
from infra.llm.openai import get_openai_llm
from infra.llm_observability.langfuse import get_langfuse_handler
from research.steps.attribute_grouping.domain.models import AttrType, ClassAttributeSet
from research.steps.context_rebuild.domain.models import GroupedChunks, GroupedContextResult
from research.steps.extraction.domain.llm_schemas import (
    build_extraction_schema,
    build_group_extraction_response_model,
)
from research.steps.extraction.domain.models import ExtractedAttributeItem, ExtractedAttributesDocument
from research.steps.extraction.domain.prompts import (
    _format_context,
    build_system_prompt,
    build_user_prompt,
)
from research.steps.merge.domain.models import MergedChunk
from research.steps.reranking.domain.models import RerankChunk

logger = logging.getLogger(__name__)
_WS_RE = re.compile(r"\s+")


def _normalize_for_exact_name_match(text: str) -> str:
    return _WS_RE.sub(" ", text.replace("\u00a0", " ")).strip().casefold()


def _source_contains_attribute_name(attr_name: str, content: str) -> bool:
    normalized_content = _normalize_for_exact_name_match(content)
    normalized_name = _normalize_for_exact_name_match(attr_name)
    return bool(normalized_name) and normalized_name in normalized_content


def _best_rerank_chunks_by_section(chunks: list[RerankChunk]) -> dict[int, RerankChunk]:
    best_by_section: dict[int, RerankChunk] = {}
    for chunk in chunks:
        current = best_by_section.get(chunk.section_id)
        if current is None or chunk.rerank_score > current.rerank_score:
            best_by_section[chunk.section_id] = chunk
    return best_by_section


def _resolve_cited_section_score(
    attribute_id: str,
    source_section_id: int | None,
    score_index: dict[str, dict[int, float]],
) -> tuple[float, int | None]:
    if source_section_id is None:
        return 0.0, None
    return float(score_index.get(attribute_id, {}).get(source_section_id, 0.0)), source_section_id


def _make_error_item(
    attribute_id: str,
    raw_quote: str | None = None,
    reasoning: str | None = None,
) -> ExtractedAttributeItem:
    return ExtractedAttributeItem(
        attribute_id=attribute_id,
        value=None,
        unit=None,
        source_section_id=None,
        rerank_score=None,
        high_confidence=None,
        raw_quote=raw_quote,
        error=True,
        reasoning=reasoning,
    )


def _extract_group(
    group_attr_ids: list[str],
    context_chunks: list[MergedChunk],
    attr_has_context: dict[str, bool],
    attr_set: ClassAttributeSet,
    llm: Any,
    callbacks: list[Any],
    execution_variant: str | None,
    priority_by_point_id: dict[int, int],
) -> list[ExtractedAttributeItem]:
    attrs = attr_set.attributes

    with_chunks = [aid for aid in group_attr_ids if attr_has_context.get(aid, False)]
    no_chunks = [aid for aid in group_attr_ids if not attr_has_context.get(aid, False)]
    error_items = [_make_error_item(aid) for aid in no_chunks]

    if not with_chunks:
        return error_items

    if not context_chunks:
        return error_items + [_make_error_item(aid) for aid in with_chunks]

    chunks = context_chunks
    context = _format_context(chunks, priority_by_point_id=priority_by_point_id)
    chunk_count = len(chunks)
    chunk_pos_to_section_id = {i: c.section_id for i, c in enumerate(chunks, start=1)}

    schema_classes: list[type] = []
    for aid in with_chunks:
        attr = attrs[aid]
        schema_class = build_extraction_schema(
            attr.attr_type,
            chunk_count,
            has_unit=bool(attr.units),
            allowed_values=attr.allowed_values,
            units=attr.units,
        )
        schema_classes.append(schema_class)

    response_model = build_group_extraction_response_model(schema_classes)
    group_attr_items = [(i, attrs[aid]) for i, aid in enumerate(with_chunks)]

    has_hints = any(attr.descr for _, attr in group_attr_items)
    system_prompt = build_system_prompt(
        include_execution_variant=bool(execution_variant),
        has_hints=has_hints,
    )
    user_prompt = build_user_prompt(
        group_attr_items,
        context,
        execution_variant=execution_variant,
    )

    run_name = "group[{}]".format(",".join(attrs[aid].attr_name for aid in with_chunks))
    invoke_callbacks = list(callbacks)
    invoke_config: dict[str, Any] = {
        "config": {"callbacks": invoke_callbacks, "run_name": run_name},
    }

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    structured_llm = llm.with_structured_output(
        response_model,
        include_raw=True,
        method="function_calling",
    )

    try:
        out = structured_llm.invoke(messages, **invoke_config)
    except Exception as e:
        logger.exception("LLM invocation failed for group %s: %s", run_name, e)
        return error_items + [_make_error_item(aid, raw_quote=str(e)) for aid in with_chunks]

    reasoning: str | None = None
    if isinstance(out, dict) and "parsed" in out:
        raw_msg = out.get("raw")
        if raw_msg is not None:
            reasoning = raw_msg.additional_kwargs.get("lc_reasoning")
        if out.get("parsing_error") is not None or out.get("parsed") is None:
            parse_err = out.get("parsing_error") or "structured output parsing returned None"
            logger.warning("Failed to parse group JSON for %s: %s", run_name, parse_err)
            return error_items + [
                _make_error_item(aid, raw_quote=str(parse_err), reasoning=reasoning)
                for aid in with_chunks
            ]
        group_response = out["parsed"]
    else:
        group_response = out

    raw_extractions = group_response.extractions
    extracted_items: list[ExtractedAttributeItem] = []

    for i, aid in enumerate(with_chunks):
        try:
            attr = attrs[aid]
            if i >= len(raw_extractions):
                logger.warning("Missing extraction at index %d for attribute %s", i, aid)
                extracted_items.append(
                    _make_error_item(
                        aid,
                        raw_quote=f"Missing extraction at index {i}",
                        reasoning=reasoning,
                    )
                )
                continue

            parsed = raw_extractions[i]
            source_section_id = (
                chunk_pos_to_section_id[parsed.source_chunk]
                if parsed.source_chunk is not None
                else None
            )
            raw_quote = parsed.raw_quote
            requires_unit = bool(attr.units)
            unit = getattr(parsed, "unit", None) if requires_unit else None

            extracted_items.append(
                ExtractedAttributeItem(
                    attribute_id=aid,
                    value=parsed.value,
                    unit=unit,
                    source_section_id=source_section_id,
                    rerank_score=None,
                    high_confidence=None,
                    raw_quote=raw_quote,
                    error=False,
                    reasoning=reasoning,
                    requires_unit=requires_unit,
                )
            )
        except Exception as e:
            logger.exception(
                "Failed to build extraction item for attribute %s in group %s",
                aid,
                run_name,
            )
            extracted_items.append(_make_error_item(aid, raw_quote=str(e), reasoning=reasoning))

    return error_items + extracted_items


def run_extraction(
    grouped: GroupedContextResult,
    attr_set: ClassAttributeSet,
    config: dict[str, Any],
    *,
    priority_by_point_id: dict[int, int],
    execution_variant: str | None = None,
) -> ExtractedAttributesDocument:
    extraction_cfg = config["EXTRACTION"]
    conf_cfg = extraction_cfg["confidence"]
    threshold_value = float(conf_cfg["threshold_value"])
    threshold_null = float(conf_cfg["threshold_null"])
    max_second_score = float(conf_cfg["max_second_score"])
    llm_model_key = extraction_cfg["llm_model_key"]
    llm = get_openai_llm(llm_model_key, config)
    max_concurrent = int(extraction_cfg["max_concurrent_requests"])

    langfuse_handler = get_langfuse_handler()
    callbacks: list[Any] = []
    if langfuse_handler:
        callbacks.append(langfuse_handler)

    by_result = {r.attribute_id: r for r in grouped.rerank_result}
    attr_has_context = {
        aid: bool(by_result[aid].rerank_chunks) if aid in by_result else False
        for aid in attr_set.attributes
    }

    groups = grouped.groups

    with CompletionProgressCallback(len(groups), desc="Extraction", unit="group") as progress_cb:
        invoke_callbacks = list(callbacks)
        invoke_callbacks.append(progress_cb)

        def _run_group(group_item: GroupedChunks) -> list[ExtractedAttributeItem]:
            return _extract_group(
                group_attr_ids=group_item.attribute_ids,
                context_chunks=group_item.grouped_chunks,
                attr_has_context=attr_has_context,
                attr_set=attr_set,
                llm=llm,
                callbacks=invoke_callbacks,
                execution_variant=execution_variant,
                priority_by_point_id=priority_by_point_id,
            )

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            groups_results = list(executor.map(_run_group, groups))

    extractions = [item for group_result in groups_results for item in group_result]

    best_chunks_by_attr_section = {
        r.attribute_id: _best_rerank_chunks_by_section(r.rerank_chunks)
        for r in grouped.rerank_result
    }
    score_index = {
        aid: {section_id: chunk.rerank_score for section_id, chunk in chunks_by_section.items()}
        for aid, chunks_by_section in best_chunks_by_attr_section.items()
    }
    content_index: dict[int, str] = {}
    for g in groups:
        for cc in g.grouped_chunks:
            content_index[cc.section_id] = cc.content

    for ext in extractions:
        if ext.error:
            continue
        try:
            if ext.value is None:
                attr_scores = score_index[ext.attribute_id]
                best_section = max(attr_scores, key=attr_scores.__getitem__)
                best_chunk = best_chunks_by_attr_section[ext.attribute_id][best_section]
                score = float(best_chunk.rerank_score)
                ext.top_rerank_section_id = best_chunk.section_id
                ext.rerank_score = score
                ext.high_confidence = score < threshold_null
            else:
                source_section_id = ext.source_section_id
                score, resolved_section_id = _resolve_cited_section_score(
                    ext.attribute_id,
                    source_section_id,
                    score_index,
                )
                if resolved_section_id is None:
                    ext.rerank_score = 0.0
                    ext.high_confidence = False
                    continue
                attr_scores = score_index[ext.attribute_id]
                second_score = max(
                    (
                        float(s)
                        for section_id, s in attr_scores.items()
                        if section_id != resolved_section_id
                    ),
                    default=0.0,
                )
                has_exact_attr_name = _source_contains_attribute_name(
                    attr_set.attributes[ext.attribute_id].attr_name,
                    content_index[resolved_section_id],
                )
                ext.rerank_score = score
                ext.high_confidence = (
                    score >= threshold_value
                    and has_exact_attr_name
                    and second_score < max_second_score
                )
        except Exception as e:
            logger.exception(
                "Confidence scoring failed for attribute %s: %s",
                ext.attribute_id,
                e,
            )
            ext.rerank_score = 0.0
            ext.high_confidence = False

    attr_order = {k: i for i, k in enumerate(attr_set.attributes)}
    extractions.sort(key=lambda e: attr_order.get(e.attribute_id, len(attr_order)))

    logger.info(
        "Extraction complete: %d extractions from %d groups",
        len(extractions),
        len(groups),
    )
    return ExtractedAttributesDocument(extractions=extractions)
