import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import mlflow

from infra.config import get_config_and_env
from infra.research_eval.types import EvalResult


def _configure_tracking() -> None:
    config = get_config_and_env()
    tracking_uri = config.get("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)


def materialize_artifact(key: str, value: Any) -> tuple[Path, Path | None]:
    """Return artifact file path and optional temp directory to remove after logging."""
    key_path = Path(key)

    if isinstance(value, Path):
        source_path = value
    elif isinstance(value, str):
        source_path = Path(value)
    else:
        source_path = None

    if source_path is not None:
        if not source_path.is_file():
            raise FileNotFoundError(f"Artifact '{key}' points to missing file: {source_path}")
        resolved = source_path.resolve()
        if resolved.name == key_path.name:
            return resolved, None
        tmp_dir = Path(tempfile.mkdtemp())
        dest = tmp_dir / key_path.name
        shutil.copy2(resolved, dest)
        return dest, tmp_dir

    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        tmp_dir = Path(tempfile.mkdtemp())
        dest = tmp_dir / key_path.name
        dest.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dest, tmp_dir

    raise ValueError(
        f"Artifact '{key}' has unsupported type {type(value).__name__}; "
        "expected file path or JSON-serializable value"
    )


def _artifact_log_path(key: str) -> str | None:
    parent = Path(key).parent
    if str(parent) in ("", "."):
        return None
    return str(parent)


def log_eval_result(result: EvalResult) -> None:
    if result.params:
        mlflow.log_params(result.params)

    if result.metrics:
        mlflow.log_metrics(result.metrics)

    for key, value in result.artifacts.items():
        path, cleanup_dir = materialize_artifact(key, value)
        try:
            mlflow.log_artifact(str(path), artifact_path=_artifact_log_path(key))
        finally:
            if cleanup_dir is not None:
                shutil.rmtree(cleanup_dir, ignore_errors=True)


@contextmanager
def start_eval_run(experiment_name: str, run_name: str) -> Iterator[None]:
    _configure_tracking()
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name):
        yield
