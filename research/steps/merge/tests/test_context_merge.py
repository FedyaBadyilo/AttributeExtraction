"""Tests for section-based merge logic in context_merge."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from research.steps.chunking.domain.models import TableChunkMetadata, TableSeam
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
)
from research.steps.merge.domain.context_merge import (
    TABLE_GAP_MARKER,
    IndexedSplit,
    _get_structure_by_table_uid,
    _join_splits_with_header_dedup,
    _strip_table_header,
    build_merged_section,
    get_merged_chunks_for_attribute,
)
from research.steps.retrieval.domain.models import ChunkHit, ChunkPayload

_PATCH_STRUCTURE = "research.steps.merge.domain.context_merge._get_structure_chunk"
_PATCH_SPLITS = "research.steps.merge.domain.context_merge._get_table_splits_sorted"
_PATCH_SELECTED = "research.steps.merge.domain.context_merge._fetch_selected_table_chunks"
_PATCH_BY_UID = "research.steps.merge.domain.context_merge._get_structure_by_table_uid"
_PATCH_BUILD = "research.steps.merge.domain.context_merge.build_merged_section"

HEADER = "<tr><td>h1</td><td>h2</td></tr>"


def _stub_qdrant() -> MagicMock:
    return MagicMock()


def _table_split(
    index: int,
    point_id: int,
    *data_rows: str,
    seam_to_next: TableSeam | None = None,
) -> IndexedSplit:
    body = "".join(data_rows)
    content = f"<table>{HEADER}{body}</table>"
    return IndexedSplit(
        table_chunk_index=index,
        point_id=point_id,
        content=content,
        seam_to_next=seam_to_next,
    )


# --- _strip_table_header ---


def test_strip_table_header_removes_first_tr() -> None:
    content = f"<table>{HEADER}<tr><td>1</td><td>2</td></tr></table>"
    assert _strip_table_header(content) == "<table><tr><td>1</td><td>2</td></tr></table>"


def test_strip_table_header_no_tr_returns_as_is() -> None:
    content = "plain text"
    assert _strip_table_header(content) == content


# --- _join_splits_with_header_dedup ---


def test_join_splits_adjacent_cluster_keeps_one_header() -> None:
    splits = [
        _table_split(0, 0, "<tr><td>1</td><td>2</td></tr>", seam_to_next=TableSeam(kind="row")),
        _table_split(1, 1, "<tr><td>3</td><td>4</td></tr>"),
    ]
    text, ids = _join_splits_with_header_dedup(splits)
    assert text.count(HEADER) == 1
    assert text.count("<table>") == 1
    assert "<tr><td>1</td><td>2</td></tr>" in text
    assert "<tr><td>3</td><td>4</td></tr>" in text
    assert TABLE_GAP_MARKER not in text
    assert ids == [0, 1]


def test_join_splits_non_adjacent_clusters_insert_gap_marker() -> None:
    splits = [
        _table_split(0, 0, "<tr><td>1</td><td>2</td></tr>"),
        _table_split(2, 2, "<tr><td>5</td><td>6</td></tr>"),
    ]
    text, ids = _join_splits_with_header_dedup(splits)
    assert TABLE_GAP_MARKER in text
    assert text.count("<table>") == 2
    assert (
        text.index("<tr><td>1</td><td>2</td></tr>")
        < text.index(TABLE_GAP_MARKER)
        < text.index("<tr><td>5</td><td>6</td></tr>")
    )
    assert ids == [0, 2]


def test_join_splits_three_clusters_two_gaps() -> None:
    splits = [
        _table_split(0, 0, "<tr><td>a</td></tr>"),
        _table_split(2, 2, "<tr><td>b</td></tr>"),
        _table_split(5, 5, "<tr><td>c</td></tr>"),
    ]
    text, _ = _join_splits_with_header_dedup(splits)
    assert text.count(TABLE_GAP_MARKER) == 2


def test_join_splits_span_seam_stitches_one_table() -> None:
    splits = [
        _table_split(
            0,
            0,
            '<tr><td rowspan="3">big</td><td>r1</td></tr>',
            seam_to_next=TableSeam(kind="span"),
        ),
        _table_split(1, 1, "<tr><td>r2</td></tr>", seam_to_next=TableSeam(kind="span")),
        _table_split(2, 2, "<tr><td>r3</td></tr>"),
    ]
    text, ids = _join_splits_with_header_dedup(splits)
    assert text.count("<table>") == 1
    assert text.count(HEADER) == 1
    assert 'rowspan="3"' in text
    assert "<tr><td>r2</td></tr>" in text
    assert "<tr><td>r3</td></tr>" in text
    assert ids == [0, 1, 2]


def test_join_splits_cell_seam_concatenates_cell_text() -> None:
    splits = [
        _table_split(
            0,
            0,
            "<tr><td>hello </td></tr>",
            seam_to_next=TableSeam(kind="cell", cell_col=0),
        ),
        _table_split(1, 1, "<tr><td>world</td></tr>"),
    ]
    text, ids = _join_splits_with_header_dedup(splits)
    assert text.count("<table>") == 1
    assert "<tr><td>hello world</td></tr>" in text
    assert ids == [0, 1]


def test_join_splits_cols_seam_concatenates_cells_horizontally() -> None:
    splits = [
        _table_split(
            0,
            0,
            "<tr><td>a</td><td>b</td></tr>",
            seam_to_next=TableSeam(kind="cols", cell_col=2),
        ),
        _table_split(1, 1, "<tr><td>c</td><td>d</td></tr>"),
    ]
    text, ids = _join_splits_with_header_dedup(splits)
    assert text.count("<table>") == 1
    assert text.count(HEADER) == 1
    assert "<tr><td>a</td><td>b</td><td>c</td><td>d</td></tr>" in text
    assert ids == [0, 1]


# --- build_merged_section ---


def test_build_merged_section_selected_table_replaces_placeholder() -> None:
    uid = "uid-A"
    structure = f"intro\n{TABLE_PLACEHOLDER_TEMPLATE.format(uid)}\noutro"
    splits = [
        _table_split(0, 0, "<tr><td>1</td></tr>", seam_to_next=TableSeam(kind="row")),
        _table_split(1, 1, "<tr><td>2</td></tr>"),
    ]

    with (
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid], ["Section"])),
        patch(_PATCH_SELECTED, return_value=[(uid, splits[1])]),
        patch(_PATCH_SPLITS, return_value=splits),
    ):
        row = build_merged_section(
            10, [1], _stub_qdrant(), "col",
            expansion_char_budget=10000,
        )

    assert TABLE_PLACEHOLDER_TEMPLATE.format(uid) not in row.merged_text
    assert "<tr><td>2</td></tr>" in row.merged_text
    assert 10 in row.source_point_ids
    assert 1 in row.source_point_ids


def test_build_merged_section_removes_optional_placeholder_when_no_optional_split_fits() -> None:
    uid = "uid-A"
    structure = f"{TABLE_PLACEHOLDER_TEMPLATE.format(uid)}"
    huge = _table_split(0, 0, f"<tr><td>{'x' * 100}</td></tr>")

    with (
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid], [])),
        patch(_PATCH_SELECTED, return_value=[]),
        patch(_PATCH_SPLITS, return_value=[huge]),
    ):
        row = build_merged_section(
            10, [], _stub_qdrant(), "col",
            expansion_char_budget=10,
        )

    assert TABLE_PLACEHOLDER_TEMPLATE.format(uid) not in row.merged_text
    assert row.merged_text == ""
    assert row.source_point_ids == [10]


def test_build_merged_section_no_expansion_budget_includes_only_selected_splits() -> None:
    uid = "uid-A"
    structure = TABLE_PLACEHOLDER_TEMPLATE.format(uid)
    splits = [
        _table_split(0, 0, "<tr><td>1</td></tr>", seam_to_next=TableSeam(kind="row")),
        _table_split(1, 1, "<tr><td>2</td></tr>"),
    ]

    with (
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid], [])),
        patch(_PATCH_SELECTED, return_value=[(uid, splits[0])]),
        patch(_PATCH_SPLITS, return_value=splits),
    ):
        row = build_merged_section(
            10, [0], _stub_qdrant(), "col",
            expansion_char_budget=None,
        )

    assert "<tr><td>1</td></tr>" in row.merged_text
    assert "<tr><td>2</td></tr>" not in row.merged_text
    assert set(row.source_point_ids) == {10, 0}


def test_build_merged_section_fills_optional_tables_in_document_order_by_expansion_budget() -> None:
    uid_a = "uid-A"
    uid_b = "uid-B"
    structure = (
        f"{TABLE_PLACEHOLDER_TEMPLATE.format(uid_a)}\n"
        f"{TABLE_PLACEHOLDER_TEMPLATE.format(uid_b)}"
    )
    split_a0 = _table_split(0, 100, "<tr><td>aaa</td></tr>", seam_to_next=TableSeam(kind="row"))
    split_a1 = _table_split(1, 101, "<tr><td>bbb</td></tr>")
    split_b0 = _table_split(0, 200, f"<tr><td>{'c' * 100}</td></tr>")

    def _splits(qdrant, collection_name, uid):
        return {
            uid_a: [split_a0, split_a1],
            uid_b: [split_b0],
        }[uid]

    joined_a, _ = _join_splits_with_header_dedup([split_a0, split_a1])
    budget = len(f"{joined_a}\n{TABLE_PLACEHOLDER_TEMPLATE.format(uid_b)}")

    with (
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid_a, uid_b], [])),
        patch(_PATCH_SELECTED, return_value=[]),
        patch(_PATCH_SPLITS, side_effect=_splits),
    ):
        row = build_merged_section(
            10,
            [],
            _stub_qdrant(),
            "col",
            expansion_char_budget=budget,
        )

    assert "<tr><td>aaa</td></tr>" in row.merged_text
    assert "<tr><td>bbb</td></tr>" in row.merged_text
    assert "c" * 100 not in row.merged_text
    assert row.source_point_ids == [10, 100, 101]
    assert TABLE_PLACEHOLDER_TEMPLATE.format(uid_a) not in row.merged_text
    assert TABLE_PLACEHOLDER_TEMPLATE.format(uid_b) not in row.merged_text


def test_build_merged_section_raises_when_selected_placeholder_missing() -> None:
    uid = "uid-selected"
    structure = "structure text without table placeholder"
    selected = _table_split(0, 99, "<tr><td>1</td></tr>")

    with (
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid], [])),
        patch(_PATCH_SELECTED, return_value=[(uid, selected)]),
        patch(_PATCH_SPLITS, return_value=[]),
    ):
        with pytest.raises(ValueError, match="Selected table placeholder missing"):
            build_merged_section(
                10, [99], _stub_qdrant(), "col",
                expansion_char_budget=10000,
            )


def test_build_merged_section_raises_when_selected_point_not_in_source_ids() -> None:
    uid = "uid-A"
    structure = TABLE_PLACEHOLDER_TEMPLATE.format(uid)

    with (
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid], [])),
        patch(_PATCH_SELECTED, return_value=[]),
        patch(_PATCH_SPLITS, return_value=[]),
    ):
        with pytest.raises(ValueError, match="Selected table point ids not merged"):
            build_merged_section(
                10, [42], _stub_qdrant(), "col",
                expansion_char_budget=10000,
            )


def test_get_structure_by_table_uid_raises_when_not_unique() -> None:
    qdrant = MagicMock()
    point_a = MagicMock(id=1, payload={"content": "", "document_chunk_index": 0, "metadata": {}})
    point_b = MagicMock(id=2, payload={"content": "", "document_chunk_index": 1, "metadata": {}})
    qdrant.scroll.return_value = ([point_a, point_b], None)

    with pytest.raises(ValueError, match="Expected exactly 1 structure chunk"):
        _get_structure_by_table_uid(qdrant, "col", "uid-x")


def test_get_structure_by_table_uid_raises_when_missing() -> None:
    qdrant = MagicMock()
    qdrant.scroll.return_value = ([], None)

    with pytest.raises(ValueError, match="Expected exactly 1 structure chunk"):
        _get_structure_by_table_uid(qdrant, "col", "uid-x")


def _table_hit(point_id: int, table_uid: str, *, score: float = 0.9) -> ChunkHit:
    return ChunkHit(
        id=point_id,
        score=score,
        payload=ChunkPayload(
            content=f"<table>{HEADER}<tr><td>1</td></tr></table>",
            document_chunk_index=0,
            metadata=TableChunkMetadata(
                document_chunk_index=0,
                table_uid=table_uid,
                table_chunk_index=0,
            ),
        ),
    )


def test_get_merged_chunks_for_attribute_table_only_hit_merges_selected_table() -> None:
    uid = "owned-table"
    section_id = 30
    selected_point_id = 101
    structure = f"intro\n{TABLE_PLACEHOLDER_TEMPLATE.format(uid)}\noutro"
    splits = [
        _table_split(0, selected_point_id, "<tr><td>1</td></tr>"),
    ]

    with (
        patch(
            _PATCH_BY_UID,
            return_value=(section_id, structure, [uid], ["Section"]),
        ),
        patch(_PATCH_STRUCTURE, return_value=(structure, [uid], ["Section"])),
        patch(_PATCH_SELECTED, return_value=[(uid, splits[0])]),
        patch(_PATCH_SPLITS, return_value=splits),
    ):
        rows = get_merged_chunks_for_attribute(
            [_table_hit(selected_point_id, uid)],
            _stub_qdrant(),
            "col",
            expansion_char_budget_structure=3000,
            expansion_char_budget_table=8000,
        )

    assert len(rows) == 1
    row = rows[0]
    assert row.section_id == section_id
    assert selected_point_id in row.source_point_ids
    assert TABLE_PLACEHOLDER_TEMPLATE.format(uid) not in row.merged_text
    assert "<tr><td>1</td></tr>" in row.merged_text


def test_get_merged_chunks_for_attribute_table_only_hit_uses_table_budget() -> None:
    uid = "owned-table"
    section_id = 30
    selected_point_id = 101

    def _fake_build(sec_id, selected_table_ids, qdrant, collection_name, **kwargs):
        assert sec_id == section_id
        assert selected_table_ids == [selected_point_id]
        assert kwargs == {"expansion_char_budget": 8000}
        return MagicMock(section_id=section_id)

    with (
        patch(_PATCH_BY_UID, return_value=(section_id, "", [uid], ["Section"])),
        patch(_PATCH_BUILD, side_effect=_fake_build),
    ):
        rows = get_merged_chunks_for_attribute(
            [_table_hit(selected_point_id, uid)],
            _stub_qdrant(),
            "col",
            expansion_char_budget_structure=3000,
            expansion_char_budget_table=8000,
        )

    assert len(rows) == 1
    assert rows[0].section_id == section_id
