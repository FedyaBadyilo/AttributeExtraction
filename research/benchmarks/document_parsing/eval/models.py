"""Evaluation records persisted in the benchmark snapshot."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from research.benchmarks.document_parsing.scoring import DocumentScores


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseArtifactPaths(_StrictModel):
    gt: str
    pred_canonical: str
    pred_raw: str | None
    ocr: str
    formatted: str


class CaseEvalRecord(_StrictModel):
    case_id: str
    data_source: str
    doc_type: str
    technical_tags: list[str]
    purpose: str
    status: Literal["ok"] = "ok"
    scores: DocumentScores
    artifacts: CaseArtifactPaths


__all__ = ["CaseArtifactPaths", "CaseEvalRecord"]
