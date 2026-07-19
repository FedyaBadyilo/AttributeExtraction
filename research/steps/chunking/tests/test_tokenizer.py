import pytest

from research.steps.chunking.domain.splitters import make_token_count_fn

MODEL = "deepvk/USER-bge-m3"


@pytest.fixture(scope="module")
def count_tokens():
    return make_token_count_fn(MODEL, add_special_tokens=True)


def test_empty_text_returns_zero(count_tokens) -> None:
    assert count_tokens("   ") == 0
    assert count_tokens("") == 0


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Технические характеристики изделия.", 7),
        ("# **1. Общие сведения**\n", 10),
        (
            "Настоящий стандарт распространяется на трубы стальные бесшовные "
            "для трубопроводов. Трубы изготавливают горячей или холодной деформацией.",
            37,
        ),
        ("| Диаметр, мм | Толщина стенки, мм |\n| --- | --- |\n| 159 | 6 |", 34),
    ],
)
def test_token_counts_match_embedder_tokenizer(count_tokens, text: str, expected: int) -> None:
    assert count_tokens(text) == expected


def test_count_fn_is_cached(count_tokens) -> None:
    text = "DN 150, PN 16, класс прочности К52."
    first = count_tokens(text)
    second = count_tokens(text)
    assert first == second == 15
