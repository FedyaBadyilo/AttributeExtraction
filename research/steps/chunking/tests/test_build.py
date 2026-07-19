"""Tests for structure/table chunk emission and table ownership metadata."""

from unittest.mock import patch

from research.steps.chunking.domain.build import (
    ChunkWalkerState,
    _table_uids_in_content,
)
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
)


def test_table_uids_in_content_preserves_document_order() -> None:
    uid_a, uid_b = "aaa-111", "bbb-222"
    content = (
        f"intro {TABLE_PLACEHOLDER_TEMPLATE.format(uid_a)} "
        f"mid {TABLE_PLACEHOLDER_TEMPLATE.format(uid_b)} outro"
    )
    assert _table_uids_in_content(content) == [uid_a, uid_b]


def test_table_uids_in_content_deduplicates_repeated_placeholder() -> None:
    uid = "dup-uid"
    content = (
        f"{TABLE_PLACEHOLDER_TEMPLATE.format(uid)} "
        f"again {TABLE_PLACEHOLDER_TEMPLATE.format(uid)}"
    )
    assert _table_uids_in_content(content) == [uid]


@patch("research.steps.chunking.domain.build.split_structure_text")
def test_emit_structure_chunk_split_assigns_table_uids_only_to_owning_part(
    mock_split_structure_text,
) -> None:
    uid_in_last_part = "table-in-last-part"
    uid_only_in_metadata = "metadata-only-uid"
    placeholder = TABLE_PLACEHOLDER_TEMPLATE.format(uid_in_last_part)
    part_without_table = "structure part without tables"
    part_with_table = f"structure part with {placeholder}"

    mock_split_structure_text.return_value = [part_without_table, part_with_table]

    state = ChunkWalkerState(
        max_chunk_tokens=1,
        min_chunk_tokens=0,
        token_count_fn=len,
        file_name="example.pdf",
    )
    state.text_buffer = [part_without_table + part_with_table]
    state.table_uids = [uid_only_in_metadata, uid_in_last_part]
    state.emit_structure_chunk()

    assert len(state.chunks) == 2
    assert state.chunks[0].metadata.table_uids == []
    assert state.chunks[1].metadata.table_uids == [uid_in_last_part]
    assert placeholder in state.chunks[1].content
    assert all(uid_only_in_metadata not in chunk.metadata.table_uids for chunk in state.chunks)


def test_emit_structure_chunk_without_split_uses_placeholders_from_content() -> None:
    uid_a, uid_b = "uid-a", "uid-b"
    content = (
        f"section {TABLE_PLACEHOLDER_TEMPLATE.format(uid_a)} "
        f"and {TABLE_PLACEHOLDER_TEMPLATE.format(uid_b)}"
    )

    state = ChunkWalkerState(
        max_chunk_tokens=10_000,
        min_chunk_tokens=0,
        token_count_fn=len,
        file_name="example.pdf",
    )
    state.text_buffer = [content]
    state.table_uids = [uid_a, uid_b, "not-in-content"]
    state.emit_structure_chunk()

    assert len(state.chunks) == 1
    assert state.chunks[0].metadata.table_uids == [uid_a, uid_b]
