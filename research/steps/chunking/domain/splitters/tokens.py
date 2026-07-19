"""Token counting via the embedder HuggingFace tokenizer."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from transformers import AutoTokenizer, PreTrainedTokenizerBase


@lru_cache(maxsize=4)
def _load_tokenizer(model: str) -> PreTrainedTokenizerBase:
    return AutoTokenizer.from_pretrained(model)


def make_token_count_fn(
    model: str,
    *,
    add_special_tokens: bool = True,
) -> Callable[[str], int]:
    """Build a cached token-count function using the embedder HuggingFace tokenizer."""
    tokenizer = _load_tokenizer(model)
    cache: dict[str, int] = {}

    def count_tokens(text: str) -> int:
        if not text.strip():
            return 0
        if text not in cache:
            cache[text] = len(tokenizer.encode(text, add_special_tokens=add_special_tokens))
        return cache[text]

    return count_tokens
