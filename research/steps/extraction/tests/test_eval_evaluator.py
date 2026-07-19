from __future__ import annotations

import json
from pathlib import Path

import pytest

from research.steps.extraction.eval.adapter import ExtractionEvalAdapter
from research.steps.extraction.eval.data import (
    build_eval_universe,
    build_ground_truth_index,
    load_predictions_for_universe,
)
from research.steps.extraction.eval.metrics import compute_metrics
from research.steps.extraction.eval.rows import build_eval_rows


def _raw_attr(
    attr_id: str,
    attr_name: str,
    attr_type: str = "Строка",
    *,
    units: list[str] | None = None,
) -> dict:
    return {
        "attr_id": attr_id,
        "attr_name": attr_name,
        "descr": None,
        "attr_type": attr_type,
        "for_extraction": True,
        "units": units,
        "allowed_values": None,
    }


def _write_extraction(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps({"extractions": rows}, ensure_ascii=False), encoding="utf-8")


def test_compute_metrics_priority_and_values() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {"c1": [_raw_attr("a1", "A1"), _raw_attr("a2", "A2"), _raw_attr("a3", "A3")]},
    )
    gt = build_ground_truth_index([
        {"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": "x"},
        {"gid": 1, "attr_id": "a2", "attr_name": "A2", "value": None},
        {"gid": 1, "attr_id": "a3", "attr_name": "A3", "value": "z"},
    ])
    predictions = {
        1: {
            "a1": _prediction("a1", "x", high_confidence=True),
            "a2": _prediction("a2", "hallucinated", high_confidence=False),
            "a3": _prediction("a3", None, high_confidence=None, error=True),
        }
    }

    rows = build_eval_rows(
        universe=universe,
        gt_index=gt,
        predictions_by_eos=predictions,
    )
    metrics = compute_metrics(rows)

    assert list(metrics) == [
        "accuracy",
        "count",
        "errors",
        "hc_rate",
        "lc_rate",
        "hc_accuracy",
        "lc_accuracy",
        "tp_rate",
        "tn_rate",
        "fp1_rate",
        "fp2_rate",
        "fn_rate",
        "tp_count",
        "tn_count",
        "fp1_count",
        "fp2_count",
        "fn_count",
    ]
    assert metrics["accuracy"] == pytest.approx(1 / 3)
    assert metrics["count"] == 3
    assert metrics["errors"] == 1
    assert metrics["hc_accuracy"] == 1
    assert metrics["lc_accuracy"] == 0
    assert metrics["tp_count"] == 1
    assert metrics["fp1_count"] == 1
    assert metrics["fn_count"] == 1


def _prediction(
    attr_id: str,
    value: object,
    *,
    high_confidence: bool | None,
    error: bool = False,
) -> object:
    from research.steps.extraction.eval.models import PredictionSlot

    return PredictionSlot(
        eos_id=1,
        attr_id=attr_id,
        value=value,
        high_confidence=high_confidence,
        error=error,
    )


def test_missing_gt_row_fails_fast() -> None:
    universe = build_eval_universe(
        [{"eos_id": 1, "class_code": "c1"}],
        {"c1": [_raw_attr("a1", "A1")]},
    )

    with pytest.raises(ValueError, match="Missing GT row"):
        build_eval_rows(
            universe=universe,
            gt_index={},
            predictions_by_eos={1: {"a1": _prediction("a1", None, high_confidence=False)}},
        )


def test_duplicate_prediction_fails_fast(tmp_path: Path) -> None:
    _write_extraction(
        tmp_path / "1_extraction.json",
        [
            {"attribute_id": "a1", "value": "x"},
            {"attribute_id": "a1", "value": "y"},
        ],
    )

    with pytest.raises(ValueError, match="Duplicate prediction"):
        load_predictions_for_universe(tmp_path, [1])


def test_adapter_smoke_without_default_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "output"
    source.mkdir()
    _write_extraction(source / "1_extraction.json", [{"attribute_id": "a1", "value": "x"}])

    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_examples_manifest",
        lambda: [{"eos_id": 1, "class_code": "c1"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_class_attribute_sets",
        lambda: {"c1": [_raw_attr("a1", "A1")]},
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_ground_truth",
        lambda: [{"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": "x"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.pipeline_params_from_config",
        lambda: {"EXTRACTION.llm_model_key": "base_llm"},
    )
    monkeypatch.setattr("research.steps.extraction.eval.adapter.mlflow.log_input", lambda *args, **kwargs: None)

    result = ExtractionEvalAdapter(use_default_string_judge=False).evaluate(source)

    assert result.metrics["accuracy"] == 1
    assert result.metrics["count"] == 1
    assert result.params == {"EXTRACTION.llm_model_key": "base_llm"}
    assert "rows.jsonl" in result.artifacts
    assert "summary.json" in result.artifacts


def test_adapter_unit_matching_fails_without_gt_unit_field(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "output"
    source.mkdir()
    _write_extraction(source / "1_extraction.json", [{"attribute_id": "a1", "value": "x"}])

    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_examples_manifest",
        lambda: [{"eos_id": 1, "class_code": "c1"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_class_attribute_sets",
        lambda: {"c1": [_raw_attr("a1", "A1")]},
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_ground_truth",
        lambda: [{"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": "x"}],
    )

    with pytest.raises(ValueError, match="explicit 'unit' field"):
        ExtractionEvalAdapter(
            use_default_string_judge=False,
            use_default_unit_judge=False,
            unit_matching_enabled=True,
        ).evaluate(source)


def test_adapter_unit_judge_fake_accepts_equivalent_unit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "output"
    source.mkdir()
    _write_extraction(
        source / "1_extraction.json",
        [{"attribute_id": "a1", "value": 10, "unit": "килограмм"}],
    )

    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_examples_manifest",
        lambda: [{"eos_id": 1, "class_code": "c1"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_class_attribute_sets",
        lambda: {
            "c1": [
                _raw_attr(
                    "a1",
                    "A1",
                    attr_type="Вещественное число",
                    units=["кг"],
                )
            ]
        },
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_ground_truth",
        lambda: [{"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": 10, "unit": "кг"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.pipeline_params_from_config",
        lambda: {},
    )
    monkeypatch.setattr("research.steps.extraction.eval.adapter.mlflow.log_input", lambda *args, **kwargs: None)

    result = ExtractionEvalAdapter(
        use_default_string_judge=False,
        unit_matching_enabled=True,
        unit_judge=lambda case: case.gt_unit == "кг" and case.pred_unit == "килограмм",
    ).evaluate(source)

    assert result.metrics["accuracy"] == 1
    assert result.metrics["tp_count"] == 1
    summary = json.loads(Path(result.artifacts["summary.json"]).read_text(encoding="utf-8"))
    assert summary["unit_judge_enabled"] is True
    assert summary["unit_judge_call_count"] == 1


def test_adapter_unit_matching_uses_gt_unit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "output"
    source.mkdir()
    _write_extraction(
        source / "1_extraction.json",
        [{"attribute_id": "a1", "value": 10, "unit": "г"}],
    )

    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_examples_manifest",
        lambda: [{"eos_id": 1, "class_code": "c1"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_class_attribute_sets",
        lambda: {
            "c1": [
                _raw_attr(
                    "a1",
                    "A1",
                    attr_type="Вещественное число",
                    units=["кг", "г"],
                )
            ]
        },
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.load_ground_truth",
        lambda: [{"gid": 1, "attr_id": "a1", "attr_name": "A1", "value": 10, "unit": "кг"}],
    )
    monkeypatch.setattr(
        "research.steps.extraction.eval.adapter.pipeline_params_from_config",
        lambda: {},
    )
    monkeypatch.setattr("research.steps.extraction.eval.adapter.mlflow.log_input", lambda *args, **kwargs: None)

    result = ExtractionEvalAdapter(
        use_default_string_judge=False,
        use_default_unit_judge=False,
        unit_matching_enabled=True,
    ).evaluate(source)

    assert result.metrics["accuracy"] == 0
    assert result.metrics["fp2_count"] == 1
    summary = json.loads(Path(result.artifacts["summary.json"]).read_text(encoding="utf-8"))
    assert summary["unit_matching_enabled"] is True
    assert summary["unit_judge_enabled"] is False
