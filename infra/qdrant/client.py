"""Shared Qdrant client for research pipeline steps."""

from __future__ import annotations

from qdrant_client import QdrantClient

from infra.config import env_bool, get_config_and_env, require_env

_DEFAULT_GRPC_PORT = 6334


def get_qdrant_client(config: dict | None = None) -> QdrantClient:
    """Build a Qdrant client from ``QDRANT_URL`` (timeout / gRPC flags from config)."""
    config = config or get_config_and_env()

    kwargs: dict = {
        "url": require_env("QDRANT_URL"),
        "check_compatibility": False,
    }
    qdrant_timeout = config.get("QDRANT_TIMEOUT")
    if qdrant_timeout is not None:
        kwargs["timeout"] = int(qdrant_timeout)
    if env_bool(config.get("QDRANT_PREFER_GRPC")):
        kwargs["prefer_grpc"] = True
        kwargs["grpc_port"] = int(config.get("QDRANT_GRPC_PORT", _DEFAULT_GRPC_PORT))

    return QdrantClient(**kwargs)
