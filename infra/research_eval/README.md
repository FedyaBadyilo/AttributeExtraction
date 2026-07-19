# research_eval

Reusable evaluation core for the research pipeline: adapter contract, run orchestration, and MLflow logging.

Step-specific metrics and `--source` parsing live in `research/steps/<step_name>/eval/adapter.py`.

## Install

```bash
pip install -r requirements.research.txt
pip install -r requirements.txt
```

`infra/research_eval/tracking.py` loads env via `infra.config.get_config_and_env()` — main `requirements.txt` is required.

Copy `.env.example` to `.env` and set `MLFLOW_TRACKING_URI` for real runs.

## Contract

- `EvalResult` — Pydantic: `metrics: dict[str, float]`, `params: dict[str, str]`, `artifacts: dict[str, Any]`
- `BaseEvalAdapter` — ABC with `target: ClassVar[str]` and `evaluate(source) -> EvalResult`
- MLflow **experiment** = `adapter_cls.target`
- MLflow **run name** = CLI `--name`

## Step wiring

`research/steps/<step_name>/eval/adapter.py`:

```python
from pathlib import Path

from infra.research_eval.types import BaseEvalAdapter, EvalResult


class StepNameEvalAdapter(BaseEvalAdapter):
    target = "step_name"

    def evaluate(self, source: str | Path) -> EvalResult:
        ...
```

`research/steps/<step_name>/eval/run.py`:

```python
from infra.research_eval.cli import run_eval_cli

from research.steps.step_name.eval.adapter import StepNameEvalAdapter

if __name__ == "__main__":
    run_eval_cli(adapter_cls=StepNameEvalAdapter)
```

Step-specific CLI flags: pass `configure_parser` and `adapter_kwargs_from_args` to
`run_eval_cli`. Those kwargs are forwarded to `adapter_cls(**adapter_kwargs)`.

## Run

From repository root:

```bash
python -m research.steps.step_name.eval.run --source <source> --name <mlflow-run-name>
```

Arguments:

- `--source` — opaque input passed to the adapter
- `--name` — MLflow run name
- optional step-specific flags via `configure_parser`
## MLflow artifacts

| `artifacts[key]` value | Behavior |
|---|---|
| path to an existing file | log file (copy with `key` name if needed) |
| `dict` / `list` / scalar | serialize to JSON named `key` |
