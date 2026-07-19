"""Strict contracts for the Document Parsing Benchmark manifest v1."""

from __future__ import annotations

import re
from pathlib import Path, PureWindowsPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PageRange(_StrictModel):
    """Inclusive, one-based page range."""

    start: int = Field(ge=1)
    end: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_order(self) -> "PageRange":
        if self.end < self.start:
            raise ValueError("page range end must be greater than or equal to start")
        return self


class SourceDocument(_StrictModel):
    path: Path
    page_ranges: list[PageRange] = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: Path) -> Path:
        return _validate_repo_relative_path(path)

    @model_validator(mode="after")
    def validate_page_ranges(self) -> "SourceDocument":
        previous_end = 0
        for page_range in self.page_ranges:
            if page_range.start <= previous_end:
                raise ValueError("page ranges must be ordered and non-overlapping")
            previous_end = page_range.end
        return self


class BenchmarkInput(_StrictModel):
    path: Path
    sha256: str

    @field_validator("path")
    @classmethod
    def validate_path(cls, path: Path) -> Path:
        return _validate_repo_relative_path(path)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
        return value


class RenderScanTransformation(_StrictModel):
    op: Literal["render_scan"]
    dpi: int = Field(gt=0)
    color_mode: Literal["grayscale", "rgb"]


class BenchmarkCase(_StrictModel):
    case_id: str
    data_source: str = Field(min_length=1)
    doc_type: str = Field(min_length=1)
    technical_tags: list[str]
    purpose: str = Field(min_length=1)
    source: SourceDocument
    transformations: list[RenderScanTransformation]
    input: BenchmarkInput
    reference_path: Path

    @field_validator("case_id")
    @classmethod
    def validate_case_id(cls, value: str) -> str:
        if not _CASE_ID_RE.fullmatch(value):
            raise ValueError("case_id may contain only letters, digits, '.', '_' and '-'")
        return value

    @field_validator("reference_path")
    @classmethod
    def validate_reference_path(cls, path: Path) -> Path:
        return _validate_repo_relative_path(path)


class BenchmarkManifest(_StrictModel):
    schema_version: Literal[1]
    cases: list[BenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cases(self) -> "BenchmarkManifest":
        case_ids: set[str] = set()
        source_selections: set[tuple[str, tuple[tuple[int, int], ...]]] = set()

        for case in self.cases:
            if case.case_id in case_ids:
                raise ValueError(f"duplicate case_id: {case.case_id}")
            case_ids.add(case.case_id)

            source_selection = (
                case.source.path.as_posix(),
                tuple((page.start, page.end) for page in case.source.page_ranges),
            )
            if source_selection in source_selections:
                raise ValueError(
                    "duplicate source path and page ranges: "
                    f"{case.source.path.as_posix()} {source_selection[1]}"
                )
            source_selections.add(source_selection)

        return self


def _validate_repo_relative_path(path: Path) -> Path:
    if (
        path.is_absolute()
        or PureWindowsPath(str(path)).is_absolute()
        or not path.parts
        or ".." in path.parts
    ):
        raise ValueError("path must be repository-relative and may not contain '..'")
    if path == Path("."):
        raise ValueError("path must point to a repository file")
    return path


__all__ = [
    "BenchmarkCase",
    "BenchmarkInput",
    "BenchmarkManifest",
    "PageRange",
    "RenderScanTransformation",
    "SourceDocument",
]
