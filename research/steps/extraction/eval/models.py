from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from research.steps.attribute_grouping.domain.models import AttrType

BaseLabel = Literal["TP", "TN", "FP_1", "FP_2", "FN"]
ConfidenceLabel = Literal["HC", "LC"]
SlotKey = tuple[int, str]


class EvalAttribute(BaseModel):
    model_config = {"extra": "forbid"}

    eos_id: int
    class_code: str
    attr_id: str
    attr_name: str
    attr_type: AttrType
    has_unit: bool = False


class GroundTruthSlot(BaseModel):
    model_config = {"extra": "forbid"}

    eos_id: int
    attr_id: str
    attr_name: str
    value: Any = None
    unit: str | None = None


class PredictionSlot(BaseModel):
    model_config = {"extra": "forbid"}

    eos_id: int
    attr_id: str
    value: Any = None
    unit: str | None = None
    raw_quote: str | None = None
    source_section_id: int | None = None
    top_rerank_section_id: int | None = None
    rerank_score: float | None = None
    high_confidence: bool | None = None
    error: bool = False


class StringJudgeCase(BaseModel):
    model_config = {"extra": "forbid"}

    eos_id: int
    attr_id: str
    attr_name: str
    gt_value: str
    pred_value: str
    raw_quote: str | None = None


class UnitJudgeCase(BaseModel):
    model_config = {"extra": "forbid"}

    eos_id: int
    attr_id: str
    attr_name: str
    gt_unit: str
    pred_unit: str


class MatchResult(BaseModel):
    model_config = {"extra": "forbid"}

    value_match: bool
    unit_match: bool | None = None
    is_match: bool
    match_method: str
    unit_match_method: str | None = None
    string_judge_used: bool = False
    unit_judge_used: bool = False


class EvalRow(BaseModel):
    model_config = {"extra": "forbid"}

    eos_id: int
    class_code: str
    attr_id: str
    attr_name: str
    attr_type: AttrType
    gt_value: Any = None
    gt_unit: str | None = None
    pred_value: Any = None
    pred_unit: str | None = None
    raw_quote: str | None = None
    source_section_id: int | None = None
    top_rerank_section_id: int | None = None
    rerank_score: float | None = None
    high_confidence: bool | None = None
    extraction_error: bool = False
    value_match: bool
    unit_match: bool | None = None
    is_match: bool
    match_method: str
    unit_match_method: str | None = None
    string_judge_used: bool = False
    unit_judge_used: bool = False
    base_label: BaseLabel
    confidence_label: ConfidenceLabel


class EvalSummary(BaseModel):
    model_config = {"extra": "forbid"}

    unit_matching_enabled: bool = False
    unit_matching_note: str = Field(
        default=(
            "Unit matching is disabled. Enable with --unit-matching when "
            "ground_truth.jsonl rows include an explicit unit field."
        )
    )
    string_judge_enabled: bool
    string_judge_call_count: int = 0
    unit_judge_enabled: bool = False
    unit_judge_call_count: int = 0
    source: str
