from research.steps.merge.domain.models import MergedChunk, MergeResult


def _merged_chunk(source_point_ids: list[int]) -> MergedChunk:
    return MergedChunk(
        source_point_ids=source_point_ids,
        display_point_id=source_point_ids[0],
        content="content",
        header_path=[],
        section_id=source_point_ids[0],
    )


def test_source_point_ids_are_order_invariant() -> None:
    assert _merged_chunk([2, 1, 3]).source_point_ids == _merged_chunk([3, 2, 1]).source_point_ids


def test_source_point_ids_are_deduplicated() -> None:
    assert _merged_chunk([1, 1, 2]).source_point_ids == (1, 2)


def test_source_point_ids_differ_for_different_sets() -> None:
    assert _merged_chunk([1]).source_point_ids != _merged_chunk([2]).source_point_ids


def test_source_point_ids_serialize_as_json_array() -> None:
    assert '"source_point_ids":[1,2]' in _merged_chunk([2, 1]).model_dump_json()


def test_merge_result_contract_serializes_attribute_chunks() -> None:
    result = MergeResult(attribute_id="attr-1", merged_chunks=[_merged_chunk([2, 1])])
    payload = result.model_dump(mode="json")

    assert payload["attribute_id"] == "attr-1"
    assert payload["merged_chunks"][0]["source_point_ids"] == [1, 2]
