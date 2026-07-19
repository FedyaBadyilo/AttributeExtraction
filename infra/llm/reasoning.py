from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI


def extract_think_content(text: str) -> tuple[str | None, str]:
    """Parse think blocks from model output (Qwen-style and Gemma 4-style)."""
    patterns = [
        ("<think>", "</think>"),
        ("<|channel>thought\n", "<channel|>"),
    ]
    for open_tag, close_tag in patterns:
        if open_tag not in text:
            continue
        _, _, after_start = text.partition(open_tag)
        if close_tag not in after_start:
            return after_start.strip() or None, ""
        reasoning, _, content = after_start.partition(close_tag)
        return reasoning.strip() or None, content.strip()
    return None, text


def _extract_api_reasoning(response: Any) -> str | None:
    if isinstance(response, dict):
        msg_d = (response.get("choices") or [{}])[0].get("message") or {}
        for key in ("reasoning", "reasoning_content"):
            value = msg_d.get(key)
            if value is not None and str(value).strip():
                return str(value)
        return None

    if not hasattr(response, "choices") or not response.choices:
        return None

    raw_msg = response.choices[0].message
    for attr in ("reasoning", "reasoning_content"):
        value = getattr(raw_msg, attr, None)
        if value is not None and str(value).strip():
            return str(value)

    extra = getattr(raw_msg, "model_extra", None)
    if isinstance(extra, dict):
        for key in ("reasoning", "reasoning_content"):
            value = extra.get(key)
            if value is not None and str(value).strip():
                return str(value)
    return None


class ReasoningChatOpenAI(ChatOpenAI):
    """Normalize reasoning API fields and/or think blocks into `additional_kwargs['lc_reasoning']`."""

    def _create_chat_result(
        self,
        response: Any,
        generation_info: dict[str, Any] | None = None,
    ) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        if not result.generations:
            return result

        ai = result.generations[0].message
        if not isinstance(ai, AIMessage):
            return result

        try:
            api_reasoning = _extract_api_reasoning(response)
        except (AttributeError, IndexError, KeyError, TypeError):
            api_reasoning = None

        think_reasoning, clean_content = extract_think_content(ai.content or "")

        if api_reasoning:
            ai.additional_kwargs["lc_reasoning"] = api_reasoning
            if think_reasoning:
                ai.content = clean_content
        elif think_reasoning:
            ai.additional_kwargs["lc_reasoning"] = think_reasoning
            ai.content = clean_content
        else:
            ai.additional_kwargs.pop("lc_reasoning", None)

        return result
