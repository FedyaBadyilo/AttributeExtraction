from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    metrics: dict[str, float] = Field(default_factory=dict)
    params: dict[str, str] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)


class BaseEvalAdapter(ABC):
    target: ClassVar[str]

    @abstractmethod
    def evaluate(self, source: str | Path) -> EvalResult:
        """Evaluate step output and return scalar metrics plus optional artifacts."""
        raise NotImplementedError
