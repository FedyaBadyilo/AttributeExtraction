from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field, create_model

from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.attribute_grouping.domain.prompts import (
    build_system_prompt,
    format_attrs_for_prompt,
)

LANGFUSE_TRACE_NAME = "attribute_grouping.llm_split"


def build_response_schema(
    partition_attr_ids: list[str],
    min_group_size: int,
    max_group_size: int,
) -> type[BaseModel]:
    enum_ids = sorted(set(partition_attr_ids))
    return create_model(
        "ResponseModel",
        __base__=BaseModel,
        groups=(
            list[list[str]],
            Field(
                ...,
                description=(
                    "Groups of attributes to extract together; "
                    "each id from enum; size within bounds."
                ),
                json_schema_extra={
                    "items": {
                        "type": "array",
                        "minItems": min_group_size,
                        "maxItems": max_group_size,
                        "items": {"type": "string", "enum": enum_ids},
                    },
                },
            ),
        ),
    )


def _merge_non_overlapping_groups(
    groups: list[list[str]],
    *,
    min_group_size: int,
    max_group_size: int,
) -> list[list[str]]:
    seen: set[str] = set()
    out: list[list[str]] = []
    for g in groups:
        if not (min_group_size <= len(g) <= max_group_size):
            continue
        if seen & set(g):
            continue
        seen.update(g)
        out.append(g)
    return out


def split_partition(
    partition_attr_ids: list[str],
    attrs_by_id: dict[str, ClassAttribute],
    llm: ChatOpenAI,
    callbacks: list | None,
    *,
    min_group_size: int,
    max_group_size: int,
) -> list[list[str]]:
    if len(partition_attr_ids) <= 1:
        return []

    ResponseModel = build_response_schema(partition_attr_ids, min_group_size, max_group_size)
    user_text = (
        "<attributes>\n{attrs}\n</attributes>\n\n"
        "Return high-confidence groups of {min_size}\u2013{max_size} attributes. "
        "Do not force uncertain attributes into mixed groups."
    ).format(
        attrs=format_attrs_for_prompt(partition_attr_ids, attrs_by_id),
        min_size=min_group_size,
        max_size=max_group_size,
    )
    messages = [
        SystemMessage(content=build_system_prompt(min_group_size, max_group_size)),
        HumanMessage(content=user_text),
    ]
    structured_llm = llm.with_structured_output(ResponseModel, method="function_calling")
    invoke_kwargs: dict = {}
    if callbacks:
        invoke_kwargs["config"] = {
            "callbacks": callbacks,
            "run_name": LANGFUSE_TRACE_NAME,
            "metadata": {"langfuse_trace_name": LANGFUSE_TRACE_NAME},
        }
    result = structured_llm.invoke(messages, **invoke_kwargs)
    return _merge_non_overlapping_groups(
        result.groups,
        min_group_size=min_group_size,
        max_group_size=max_group_size,
    )
