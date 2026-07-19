from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from research.steps.extraction.eval.models import EvalRow, EvalSummary


def _dump_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def _error_row(row: EvalRow) -> dict[str, Any]:
    return {
        "eos_id": row.eos_id,
        "attr_id": row.attr_id,
        "attr_name": row.attr_name,
        "attr_type": row.attr_type.value,
        "gt_value": row.gt_value,
        "pred_value": row.pred_value,
        "base_label": row.base_label,
        "confidence_label": row.confidence_label,
        "raw_quote": row.raw_quote,
        "match_method": row.match_method,
    }


def write_artifacts(
    *,
    rows: list[EvalRow],
    summary: EvalSummary,
) -> dict[str, Path]:
    artifact_dir = Path(tempfile.mkdtemp(prefix="extraction-eval-"))
    rows_path = artifact_dir / "rows.jsonl"
    summary_path = artifact_dir / "summary.json"
    _dump_jsonl(rows_path, [row.model_dump(mode="json") for row in rows])
    _dump_json(summary_path, summary.model_dump(mode="json"))

    artifacts = {
        "summary.json": summary_path,
        "rows.jsonl": rows_path,
    }
    error_groups = {
        "errors/fp_1.json": [row for row in rows if row.base_label == "FP_1"],
        "errors/fp_2.json": [row for row in rows if row.base_label == "FP_2"],
        "errors/fn.json": [row for row in rows if row.base_label == "FN"],
        "errors/technical.json": [row for row in rows if row.extraction_error],
    }
    for key, group_rows in error_groups.items():
        path = artifact_dir / Path(key).name
        _dump_json(path, [_error_row(row) for row in group_rows])
        artifacts[key] = path
    return artifacts
