from __future__ import annotations

import numpy as np

from infra.llm.embeddings import get_openai_embeddings
from research.steps.attribute_grouping.domain.models import ClassAttribute


def build_embedding_text(attr: ClassAttribute) -> str:
    if attr.descr is not None:
        return f"{attr.attr_name} | {attr.descr}"
    return attr.attr_name


def embed_texts(texts: list[str], model_name: str, config: dict) -> np.ndarray:
    embedder = get_openai_embeddings(model_name, config)
    vectors = embedder.embed_documents(texts)
    return np.array(vectors, dtype=np.float32)


def cosine_similarity_matrix(emb: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(emb, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    x = emb / norms
    return x @ x.T
