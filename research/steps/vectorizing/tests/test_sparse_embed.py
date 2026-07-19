from research.steps.vectorizing.domain.sparse_embed import (
    embed_sparse_documents,
    embed_sparse_queries,
)


def test_embed_sparse_documents_returns_vectors() -> None:
    vectors = embed_sparse_documents(["требования к электроприводам"])
    assert len(vectors) == 1
    assert len(vectors[0].indices) > 0
    assert len(vectors[0].values) == len(vectors[0].indices)


def test_embed_sparse_queries_returns_vectors() -> None:
    vectors = embed_sparse_queries(["электропривод"])
    assert len(vectors) == 1
    assert len(vectors[0].indices) > 0
    assert len(vectors[0].values) == len(vectors[0].indices)


def test_embed_sparse_empty_input() -> None:
    assert embed_sparse_documents([]) == []
    assert embed_sparse_queries([]) == []
