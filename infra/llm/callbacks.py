from __future__ import annotations

import threading

from langchain_core.callbacks import BaseCallbackHandler
from tqdm import tqdm


class CompletionProgressCallback(BaseCallbackHandler):
    """Update a single tqdm progress bar after each completed LLM call.

    Thread-safe for use with ``runnable.batch()``.
    """

    def __init__(self, total: int, desc: str = "Completion", unit: str = "attr") -> None:
        super().__init__()
        self._total = total
        self._lock = threading.Lock()
        self._pbar = tqdm(total=total, desc=desc, unit=unit)

    def on_llm_end(self, response: object, **kwargs: object) -> None:
        with self._lock:
            self._pbar.update(1)

    def close(self) -> None:
        self._pbar.close()

    def __enter__(self) -> CompletionProgressCallback:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
