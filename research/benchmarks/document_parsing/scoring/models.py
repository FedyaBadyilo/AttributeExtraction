"""Pydantic result contracts for document parsing scores."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoreModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TextScores(ScoreModel):
    cer: float = Field(ge=0.0, le=1.0)
    wer: float = Field(ge=0.0, le=1.0)
    token_precision: float = Field(ge=0.0, le=1.0)
    token_recall: float = Field(ge=0.0, le=1.0)
    token_f1: float = Field(ge=0.0, le=1.0)


class TablePairScore(ScoreModel):
    position: int = Field(ge=0)
    pred_present: bool
    gt_present: bool
    teds: float = Field(ge=0.0, le=1.0)
    teds_structure: float = Field(ge=0.0, le=1.0)


class TableScores(ScoreModel):
    pred_count: int = Field(ge=0)
    gt_count: int = Field(ge=0)
    pairs: list[TablePairScore]
    teds: float = Field(ge=0.0, le=1.0)
    teds_structure: float = Field(ge=0.0, le=1.0)


class CountComparison(ScoreModel):
    pred: int = Field(ge=0)
    gt: int = Field(ge=0)
    delta: int
    similarity: float = Field(ge=0.0, le=1.0)


class StructuralCountScores(ScoreModel):
    heading_levels: dict[int, CountComparison]
    table_blocks: CountComparison
    data_rows: CountComparison
    similarity: float = Field(ge=0.0, le=1.0)


class SequenceScores(ScoreModel):
    pred_count: int = Field(ge=0)
    gt_count: int = Field(ge=0)
    lcs_length: int = Field(ge=0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)


class StructureScores(ScoreModel):
    counts: StructuralCountScores
    headings: SequenceScores
    ast_similarity: float = Field(ge=0.0, le=1.0)


class DocumentScores(ScoreModel):
    text: TextScores
    tables: TableScores
    structure: StructureScores
    table_parse_error: str | None = None
