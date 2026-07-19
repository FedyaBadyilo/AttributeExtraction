from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent

logger = logging.getLogger(__name__)


def config_logger() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def _resolve_config_path(config_path: str | os.PathLike[str]) -> Path:
    """Resolve config path relative to repository root."""
    path = Path(config_path)
    if path.is_absolute():
        return path
    return (_project_root / path).resolve()


def get_config_and_env(
    config_path: str | os.PathLike[str] = "config.yaml",
) -> dict:
    """Load YAML config and merge with environment variables.

    Top-level env keys override YAML keys. Nested YAML structures are preserved.
    """
    load_dotenv(_project_root / ".env")
    config_file = _resolve_config_path(config_path)
    with config_file.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if config is None:
        config = {}

    env = dict(os.environ)
    return {**config, **env}
