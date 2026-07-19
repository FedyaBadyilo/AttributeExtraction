"""Search query construction from catalog attributes."""

from __future__ import annotations

from typing import Any

from research.steps.attribute_grouping.domain.models import ClassAttribute


def normalize_execution_variant(execution_variant: Any) -> str | None:
    """Normalize execution variant from manifest into a compact string or None."""
    if execution_variant is None:
        return None
    value = str(execution_variant).strip()
    if not value:
        return None
    if value.lower() in {"none", "null", "n/a"}:
        return None
    return value


def build_search_query(
    attr: ClassAttribute,
    *,
    execution_variant: str | None = None,
) -> str | None:
    """Build one compact query string for dense + BM25 search."""
    name = attr.attr_name.strip()
    if not name:
        return None
    parts = [name]
    variant = normalize_execution_variant(execution_variant)
    if variant:
        parts.append("код: " + variant)
    return " | ".join(parts)
