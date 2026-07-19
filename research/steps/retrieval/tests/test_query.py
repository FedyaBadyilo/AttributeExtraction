from research.steps.attribute_grouping.domain.models import AttrType, ClassAttribute
from research.steps.retrieval.domain.query import (
    build_search_query,
    normalize_execution_variant,
)


def test_build_search_query_uses_attr_name() -> None:
    attr = ClassAttribute(
        attr_id="attr1",
        attr_name="Масса",
        attr_type=AttrType.NUMBER,
        for_extraction=True,
    )
    assert build_search_query(attr) == "Масса"


def test_build_search_query_ignores_descr() -> None:
    attr = ClassAttribute(
        attr_id="attr2",
        attr_name="Маркировка",
        descr="Описание не входит в запрос",
        attr_type=AttrType.STRING,
        for_extraction=True,
    )
    assert build_search_query(attr) == "Маркировка"


def test_build_search_query_whitespace_name_returns_none() -> None:
    attr = ClassAttribute.model_construct(
        attr_id="attr3",
        attr_name="   ",
        attr_type=AttrType.STRING,
        for_extraction=True,
    )
    assert build_search_query(attr) is None


def test_build_search_query_appends_execution_variant() -> None:
    attr = ClassAttribute(
        attr_id="attr4",
        attr_name="Масса",
        attr_type=AttrType.NUMBER,
        for_extraction=True,
    )
    assert build_search_query(attr, execution_variant="14с17п30") == "Масса | код: 14с17п30"


def test_normalize_execution_variant_rejects_empty_and_sentinels() -> None:
    assert normalize_execution_variant(None) is None
    assert normalize_execution_variant("   ") is None
    assert normalize_execution_variant("none") is None
    assert normalize_execution_variant("N/A") is None
    assert normalize_execution_variant(" 14с17п30 ") == "14с17п30"
