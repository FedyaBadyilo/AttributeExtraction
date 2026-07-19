"""Qdrant infrastructure shared across research steps."""

from infra.qdrant.client import get_qdrant_client

__all__ = ["get_qdrant_client"]
