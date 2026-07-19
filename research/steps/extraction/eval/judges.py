from __future__ import annotations

import textwrap
import threading
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from infra.config import get_config_and_env
from infra.llm.openai import get_openai_llm
from research.steps.extraction.eval.models import StringJudgeCase, UnitJudgeCase

LANGFUSE_TRACE_NAME = "extraction-eval-judge"

_STRING_SYSTEM_PROMPT = textwrap.dedent("""
    You are a value comparison judge for attribute extraction evaluation.

    Decide whether the predicted value and ground-truth value represent the same
    discrete attribute value. Treat formatting, case, minor spelling differences,
    abbreviations, and expanded forms as the same when they identify the same
    object or concept. Treat different concrete codes, grades, numbers, or
    concepts as different.

    Respond only via the structured output.
""").strip()

_UNIT_SYSTEM_PROMPT = textwrap.dedent("""
    You are a unit-of-measure comparison judge for attribute extraction evaluation.

    Decide whether the predicted unit and ground-truth unit denote the same
    physical quantity / unit of measure for the given attribute.

    Treat as the SAME unit when they are equivalent notations, including:
    - Unicode / encoding variants (e.g. °С vs ⁰C vs ℃; latin C vs cyrillic С
      next to a degree mark);
    - ASCII power vs superscript (e.g. м^3 vs м³, кг/м^3 vs кг/м³);
    - common abbreviations vs full forms (e.g. мес vs месяц);
    - optional dimensionless prefixes that do not change the unit
      (e.g. pH vs ед. pH).

    Treat as DIFFERENT units when they are different quantities or scales
    (e.g. кг vs г, м vs мм, °C vs K), or when one side is clearly not a unit
    equivalent of the other.

    Respond only via the structured output.
""").strip()


class StringValueJudgeResult(BaseModel):
    same_value: bool = Field(
        description="True when predicted and ground-truth values represent the same value.",
    )


class UnitJudgeResult(BaseModel):
    same_unit: bool = Field(
        description=(
            "True when predicted and ground-truth units denote the same "
            "unit of measure."
        ),
    )


class LLMStringJudge:
    def __init__(
        self,
        model_key: str | None = None,
        *,
        callbacks: list[Any] | None = None,
    ) -> None:
        config = get_config_and_env()
        self._model_key = model_key or config["EXTRACTION"]["llm_model_key"]
        self._llm = get_openai_llm(self._model_key, config)
        self._callbacks = list(callbacks or [])
        self._call_count_lock = threading.Lock()
        self.call_count = 0

    def __call__(self, case: StringJudgeCase) -> bool:
        with self._call_count_lock:
            self.call_count += 1
        parts = [
            f"Attribute name: {case.attr_name}",
            f"GT value: {case.gt_value!r}",
            f"Predicted value: {case.pred_value!r}",
        ]
        if case.raw_quote:
            parts.append(f"Source document quote: {case.raw_quote!r}")

        structured = self._llm.with_structured_output(
            StringValueJudgeResult,
            include_raw=True,
            method="function_calling",
        )
        run_name = f"judge[eos={case.eos_id}][{case.attr_name}]"
        invoke_kwargs: dict[str, Any] = {}
        if self._callbacks:
            invoke_kwargs["config"] = {
                "callbacks": self._callbacks,
                "run_name": run_name,
                "metadata": {"langfuse_trace_name": LANGFUSE_TRACE_NAME},
            }
        result = structured.invoke(
            [
                SystemMessage(content=_STRING_SYSTEM_PROMPT),
                HumanMessage(content="\n".join(parts)),
            ],
            **invoke_kwargs,
        )
        if isinstance(result, dict) and "parsed" in result:
            parsed = result["parsed"]
        else:
            parsed = result
        if not isinstance(parsed, StringValueJudgeResult):
            raise ValueError(
                "LLM string judge returned unexpected payload for "
                f"eos_id={case.eos_id}, attr_id={case.attr_id}: {parsed!r}"
            )
        return parsed.same_value


class LLMUnitJudge:
    def __init__(
        self,
        model_key: str | None = None,
        *,
        callbacks: list[Any] | None = None,
    ) -> None:
        config = get_config_and_env()
        self._model_key = model_key or config["EXTRACTION"]["llm_model_key"]
        self._llm = get_openai_llm(self._model_key, config)
        self._callbacks = list(callbacks or [])
        self._call_count_lock = threading.Lock()
        self.call_count = 0

    def __call__(self, case: UnitJudgeCase) -> bool:
        with self._call_count_lock:
            self.call_count += 1
        parts = [
            f"Attribute name: {case.attr_name}",
            f"GT unit: {case.gt_unit!r}",
            f"Predicted unit: {case.pred_unit!r}",
        ]

        structured = self._llm.with_structured_output(
            UnitJudgeResult,
            include_raw=True,
            method="function_calling",
        )
        run_name = f"unit-judge[eos={case.eos_id}][{case.attr_name}]"
        invoke_kwargs: dict[str, Any] = {}
        if self._callbacks:
            invoke_kwargs["config"] = {
                "callbacks": self._callbacks,
                "run_name": run_name,
                "metadata": {"langfuse_trace_name": LANGFUSE_TRACE_NAME},
            }
        result = structured.invoke(
            [
                SystemMessage(content=_UNIT_SYSTEM_PROMPT),
                HumanMessage(content="\n".join(parts)),
            ],
            **invoke_kwargs,
        )
        if isinstance(result, dict) and "parsed" in result:
            parsed = result["parsed"]
        else:
            parsed = result
        if not isinstance(parsed, UnitJudgeResult):
            raise ValueError(
                "LLM unit judge returned unexpected payload for "
                f"eos_id={case.eos_id}, attr_id={case.attr_id}: {parsed!r}"
            )
        return parsed.same_unit
