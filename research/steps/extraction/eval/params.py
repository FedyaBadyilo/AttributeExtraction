from __future__ import annotations

from infra.config import get_config_and_env


def _add_param(params: dict[str, str], key: str, value: object) -> None:
    params[key] = str(value)


def _add_model_params(
    params: dict[str, str],
    *,
    config: dict,
    section: str,
    key: str,
    registry_name: str,
) -> None:
    registry = config[registry_name]
    model_key = str(config[section][key])
    model_config = registry[model_key]
    prefix = f"{section}.{key}"
    _add_param(params, prefix, model_key)
    _add_param(params, f"{prefix}.model", model_config["model"])


def _add_nested_model_params(
    params: dict[str, str],
    *,
    config: dict,
    section: str,
    subsection: str,
    key: str,
    registry_name: str,
) -> None:
    registry = config[registry_name]
    model_key = str(config[section][subsection][key])
    model_config = registry[model_key]
    prefix = f"{section}.{subsection}.{key}"
    _add_param(params, prefix, model_key)
    _add_param(params, f"{prefix}.model", model_config["model"])


def pipeline_params_from_config() -> dict[str, str]:
    config = get_config_and_env()
    params: dict[str, str] = {}

    _add_param(params, "ATTRIBUTE_GROUPING.min_group_size", config["ATTRIBUTE_GROUPING"]["min_group_size"])
    _add_param(params, "ATTRIBUTE_GROUPING.max_group_size", config["ATTRIBUTE_GROUPING"]["max_group_size"])
    _add_param(params, "ATTRIBUTE_GROUPING.tight_sim_threshold", config["ATTRIBUTE_GROUPING"]["tight_sim_threshold"])
    _add_param(params, "ATTRIBUTE_GROUPING.max_partition_size", config["ATTRIBUTE_GROUPING"]["max_partition_size"])
    _add_param(params, "ATTRIBUTE_GROUPING.max_concurrent_requests", config["ATTRIBUTE_GROUPING"]["max_concurrent_requests"])
    _add_model_params(
        params,
        config=config,
        section="ATTRIBUTE_GROUPING",
        key="llm_model_key",
        registry_name="MODELS",
    )
    _add_model_params(
        params,
        config=config,
        section="ATTRIBUTE_GROUPING",
        key="embedder_model_key",
        registry_name="EMBEDDINGS",
    )

    _add_param(params, "CHUNKING.max_chunk_tokens", config["CHUNKING"]["max_chunk_tokens"])
    _add_param(params, "CHUNKING.min_chunk_tokens", config["CHUNKING"]["min_chunk_tokens"])
    _add_model_params(
        params,
        config=config,
        section="CHUNKING",
        key="embedder_model_key",
        registry_name="EMBEDDINGS",
    )

    _add_model_params(
        params,
        config=config,
        section="VECTORIZING",
        key="embedder_model_key",
        registry_name="EMBEDDINGS",
    )

    _add_param(params, "RETRIEVAL.embed_batch_size", config["RETRIEVAL"]["embed_batch_size"])
    _add_param(params, "RETRIEVAL.prefetch_limit_dense", config["RETRIEVAL"]["prefetch_limit_dense"])
    _add_param(params, "RETRIEVAL.prefetch_limit_bm25", config["RETRIEVAL"]["prefetch_limit_bm25"])
    _add_param(params, "RETRIEVAL.limit", config["RETRIEVAL"]["limit"])
    _add_model_params(
        params,
        config=config,
        section="RETRIEVAL",
        key="embedder_model_key",
        registry_name="EMBEDDINGS",
    )

    _add_param(params, "MERGE.expansion_char_budget_structure", config["MERGE"]["expansion_char_budget_structure"])
    _add_param(params, "MERGE.expansion_char_budget_table", config["MERGE"]["expansion_char_budget_table"])

    _add_param(params, "RERANKING.rerank.top_k", config["RERANKING"]["rerank"]["top_k"])
    _add_param(params, "RERANKING.rerank.fallback_top_k", config["RERANKING"]["rerank"]["fallback_top_k"])
    _add_param(params, "RERANKING.rerank.max_concurrent_requests", config["RERANKING"]["rerank"]["max_concurrent_requests"])
    _add_nested_model_params(
        params,
        config=config,
        section="RERANKING",
        subsection="rerank",
        key="llm_model_key",
        registry_name="MODELS",
    )
    _add_param(
        params,
        "RERANKING.grouping.merge_chunk_jaccard_min",
        config["RERANKING"]["grouping"]["merge_chunk_jaccard_min"],
    )
    _add_param(
        params,
        "RERANKING.grouping.max_group_size",
        config["RERANKING"]["grouping"]["max_group_size"],
    )

    _add_param(params, "EXTRACTION.max_concurrent_requests", config["EXTRACTION"]["max_concurrent_requests"])
    _add_param(params, "EXTRACTION.confidence.threshold_value", config["EXTRACTION"]["confidence"]["threshold_value"])
    _add_param(params, "EXTRACTION.confidence.threshold_null", config["EXTRACTION"]["confidence"]["threshold_null"])
    _add_param(params, "EXTRACTION.confidence.max_second_score", config["EXTRACTION"]["confidence"]["max_second_score"])
    _add_model_params(
        params,
        config=config,
        section="EXTRACTION",
        key="llm_model_key",
        registry_name="MODELS",
    )
    return params
