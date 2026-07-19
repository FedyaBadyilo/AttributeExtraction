"""Traceability parameters for document parsing benchmark runs."""

from __future__ import annotations

from typing import Literal

from infra.config import get_config_and_env
from research.benchmarks.document_parsing.canonicalize import (
    CANONICALIZATION_VERSION,
)
from research.benchmarks.document_parsing.scoring import METRIC_CONTRACT_VERSION
from research.steps.ocr.domain.dedoc_parameters import DEDOC_SCALAR_PARAMETERS

_DEDOC_OPTIONS = {
    f"dedoc.{key}": value for key, value in DEDOC_SCALAR_PARAMETERS.items()
}


def benchmark_params(
    *,
    dataset_digest: str,
    manifest_schema_version: int,
    eval_mode: Literal["rebuild", "reuse"],
    config: dict | None = None,
) -> dict[str, str]:
    pipeline_config = get_config_and_env() if config is None else config
    params = {
        "metric_contract_version": METRIC_CONTRACT_VERSION,
        "canonicalization_version": CANONICALIZATION_VERSION,
        "manifest_schema_version": str(manifest_schema_version),
        "dataset_digest": dataset_digest,
        "eval_mode": eval_mode,
        "OCR.on_gpu": str(bool(pipeline_config["OCR"]["on_gpu"])),
    }
    params.update(_DEDOC_OPTIONS)
    return params


__all__ = ["benchmark_params"]
