from pathlib import Path
from typing import Any

from infra.research_eval.tracking import log_eval_result, start_eval_run
from infra.research_eval.types import BaseEvalAdapter, EvalResult


def evaluate_experiment(
    adapter_cls: type[BaseEvalAdapter],
    source: str | Path,
    name: str,
    *,
    adapter_kwargs: dict[str, Any] | None = None,
) -> EvalResult:
    adapter = adapter_cls(**(adapter_kwargs or {}))
    with start_eval_run(experiment_name=adapter_cls.target, run_name=name):
        raw = adapter.evaluate(source)
        result = EvalResult.model_validate(raw)
        log_eval_result(result)
    return result
