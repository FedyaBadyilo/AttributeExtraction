from __future__ import annotations

from research.steps.extraction.eval.matching import confidence_label, label_for_case, match_values
from research.steps.extraction.eval.models import (
    EvalAttribute,
    EvalRow,
    GroundTruthSlot,
    PredictionSlot,
    SlotKey,
)


def _slot_key(eos_id: int, attr_id: str) -> SlotKey:
    return eos_id, attr_id


def build_eval_rows(
    *,
    universe: list[EvalAttribute],
    gt_index: dict[SlotKey, GroundTruthSlot],
    predictions_by_eos: dict[int, dict[str, PredictionSlot]],
    string_verdicts: dict[SlotKey, bool] | None = None,
    unit_verdicts: dict[SlotKey, bool] | None = None,
    unit_matching_enabled: bool = False,
) -> list[EvalRow]:
    rows: list[EvalRow] = []
    string_verdicts = string_verdicts or {}
    unit_verdicts = unit_verdicts or {}
    for slot in universe:
        key = _slot_key(slot.eos_id, slot.attr_id)
        if key not in gt_index:
            raise ValueError(
                f"Missing GT row for for_extraction slot eos_id={slot.eos_id}, "
                f"attr_id={slot.attr_id}"
            )
        predictions = predictions_by_eos[slot.eos_id]
        if slot.attr_id not in predictions:
            raise ValueError(
                f"Missing prediction for eos_id={slot.eos_id}, attr_id={slot.attr_id}"
            )

        gt = gt_index[key]
        pred = predictions[slot.attr_id]
        string_judge_verdict = string_verdicts.get(key)
        unit_judge_verdict = unit_verdicts.get(key)
        match = match_values(
            gt_value=gt.value,
            pred_value=pred.value,
            attr_type=slot.attr_type,
            string_judge_verdict=string_judge_verdict,
            unit_judge_verdict=unit_judge_verdict,
            gt_unit=gt.unit,
            pred_unit=pred.unit,
            unit_matching_enabled=unit_matching_enabled,
            has_unit=slot.has_unit,
        )
        base_label = label_for_case(gt.value, pred.value, match.is_match)
        conf_label = confidence_label(pred.high_confidence)
        rows.append(
            EvalRow(
                eos_id=slot.eos_id,
                class_code=slot.class_code,
                attr_id=slot.attr_id,
                attr_name=slot.attr_name,
                attr_type=slot.attr_type,
                gt_value=gt.value,
                gt_unit=gt.unit,
                pred_value=pred.value,
                pred_unit=pred.unit,
                raw_quote=pred.raw_quote,
                source_section_id=pred.source_section_id,
                top_rerank_section_id=pred.top_rerank_section_id,
                rerank_score=pred.rerank_score,
                high_confidence=pred.high_confidence,
                extraction_error=pred.error,
                value_match=match.value_match,
                unit_match=match.unit_match,
                is_match=match.is_match,
                match_method=match.match_method,
                unit_match_method=match.unit_match_method,
                string_judge_used=match.string_judge_used,
                unit_judge_used=match.unit_judge_used,
                base_label=base_label,
                confidence_label=conf_label,
            )
        )
    return rows
