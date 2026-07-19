"""Persistent storage for RAG labels via diskcache."""

from diskcache import Cache

from apps.rag_labeling.config_paths import RAG_LABELS_CACHE_DIR

_LABELS_KEY = "labels"
_USER_SET_KEY = "user_set"


def _get_cache() -> Cache:
    RAG_LABELS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return Cache(str(RAG_LABELS_CACHE_DIR))


def load_labels() -> dict:
    cache = _get_cache()
    try:
        return cache.get(_LABELS_KEY) or {}
    finally:
        cache.close()


def save_labels(labels: dict) -> None:
    cache = _get_cache()
    try:
        cache.set(_LABELS_KEY, labels)
    finally:
        cache.close()


def load_user_set() -> dict | None:
    """Load per-document sets of attr_ids explicitly set by the user."""
    cache = _get_cache()
    try:
        return cache.get(_USER_SET_KEY)
    finally:
        cache.close()


def save_user_set(user_set: dict) -> None:
    """Save user_set: eos_id (str) -> set of attr_id."""
    cache = _get_cache()
    try:
        cache.set(_USER_SET_KEY, user_set)
    finally:
        cache.close()


def clear_labels() -> None:
    cache = _get_cache()
    try:
        cache.delete(_LABELS_KEY)
        cache.delete(_USER_SET_KEY)
    finally:
        cache.close()


def clear_labels_for_eos(eos_id: int | str) -> None:
    """Remove labels and user_set entries for a single eos_id."""
    key = str(eos_id)
    cache = _get_cache()
    try:
        labels = cache.get(_LABELS_KEY) or {}
        user_set = cache.get(_USER_SET_KEY) or {}
        if key in labels:
            labels.pop(key, None)
            cache.set(_LABELS_KEY, labels)
        if key in user_set:
            user_set.pop(key, None)
            cache.set(_USER_SET_KEY, user_set)
    finally:
        cache.close()
