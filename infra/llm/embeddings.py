from __future__ import annotations

from typing import TYPE_CHECKING

from infra.config import get_config_and_env, require_env

if TYPE_CHECKING:
    from langchain_openai import OpenAIEmbeddings


def get_openai_embeddings(model_name: str, config: dict | None = None) -> OpenAIEmbeddings:
    """Build OpenAI embeddings from config EMBEDDINGS[model_name]."""
    from langchain_openai import OpenAIEmbeddings

    if config is None:
        config = get_config_and_env()
    embedding_config = dict(config["EMBEDDINGS"][model_name])
    embedding_config.pop("openai_api_key", None)
    embedding_config.pop("openai_api_base", None)
    embedding_config["openai_api_key"] = require_env("OPENAI_API_KEY")
    embedding_config["openai_api_base"] = require_env("EMBEDDINGS_BASE_URL")
    return OpenAIEmbeddings(**embedding_config)
