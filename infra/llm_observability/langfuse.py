from __future__ import annotations

import logging

import httpx

from infra.config import env_bool, get_config_and_env

logger = logging.getLogger(__name__)


def create_langfuse_handler(
    enabled: bool,
    url: str,
    public: str,
    secret: str,
    debug: bool | None = False,
):
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler

    if not enabled or url is None:
        return None

    logger.info("Langfuse URL set to '%s'", url)

    if not public or not secret:
        logger.warning(
            "Langfuse URL was specified, but credentials were missing; tracing disabled",
        )
        return None

    logger.info("Tracing enabled")

    httpx_client = httpx.Client(verify=False, cert=None)
    try:
        Langfuse(
            host=url,
            secret_key=secret,
            public_key=public,
            debug=debug,
            httpx_client=httpx_client,
        )
        logger.info("Langfuse client initialized")
    except Exception as e:
        logger.error("Langfuse initialization failed: %s", e)
        httpx_client.close()
        return None

    return CallbackHandler(public_key=public)


def get_langfuse_handler():
    """Create a Langfuse callback handler for LLM tracing."""
    config = get_config_and_env()
    return create_langfuse_handler(
        enabled=env_bool(config.get("LANGFUSE_ENABLE"), default=False),
        url=config.get("LANGFUSE_BASE_URL"),
        public=config.get("LANGFUSE_PUBLIC_KEY"),
        secret=config.get("LANGFUSE_SECRET_KEY"),
        debug=env_bool(config.get("LANGFUSE_DEBUG"), default=False),
    )
