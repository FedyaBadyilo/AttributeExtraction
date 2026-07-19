from __future__ import annotations

from infra.config import get_config_and_env, require_env
from infra.llm.reasoning import ReasoningChatOpenAI


def get_openai_llm(model_name: str, config: dict | None = None) -> ReasoningChatOpenAI:
    """Build an OpenAI chat model from config MODELS[model_name]."""
    if config is None:
        config = get_config_and_env()
    llm_config = dict(config["MODELS"][model_name])
    llm_config.pop("openai_api_key", None)
    llm_config.pop("base_url", None)
    llm_config["openai_api_key"] = require_env("OPENAI_API_KEY")
    llm_config["base_url"] = require_env("OPENAI_BASE_URL")
    return ReasoningChatOpenAI(**llm_config)
