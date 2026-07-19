"""Backend settings. Paths resolve under the app dir; config comes from repo root."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT.parent
REPO_ROOT = APP_ROOT.parent.parent


class Settings(BaseSettings):
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)
    backend_cache_dir: str = Field(default="backend/.cache")
    backend_sqlite_path: str = Field(default="backend/.cache/backend.sqlite3")
    backend_log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cache_dir(self) -> Path:
        return self._resolve_path(self.backend_cache_dir)

    @property
    def sqlite_path(self) -> Path:
        return self._resolve_path(self.backend_sqlite_path)

    @property
    def reference_data_dir(self) -> Path:
        return BACKEND_ROOT / "reference_data"

    @property
    def registry_templates_dir(self) -> Path:
        return BACKEND_ROOT / "templates" / "registry"

    @staticmethod
    def _resolve_path(value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (APP_ROOT / path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
