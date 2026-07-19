"""Tests for placeholder block removal."""

from research.steps.common.downstream_text import remove_placeholder_blocks
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
)


def test_remove_placeholder_blocks_strips_attachment_blocks() -> None:
    content = (
        "\n<attachment attach_c60cc382-e522-4a37-ba86-8f735ce0f88a>\n\n"
        "\n<attachment attach_848fcf06-1848-4320-b859-4aeb1829c27c>\n\n"
    )

    assert remove_placeholder_blocks(content) == ""


def test_remove_placeholder_blocks_strips_table_blocks() -> None:
    uid_a = "84a00e5b-0000-0000-0000-000000000001"
    uid_b = "5755ea1f-0000-0000-0000-000000000002"
    content = (
        "## **Таблица Б.2**\n\n"
        f"\n{TABLE_PLACEHOLDER_TEMPLATE.format(uid_a)}\n\n"
        f"\n{TABLE_PLACEHOLDER_TEMPLATE.format(uid_b)}\n\n"
    )

    assert remove_placeholder_blocks(content) == "## **Таблица Б.2**\n\n"


def test_remove_placeholder_blocks_preserves_surrounding_text() -> None:
    content = (
        "before\n<attachment attach_123>\n\n"
        f"middle\n{TABLE_PLACEHOLDER_TEMPLATE.format('table_456')}\n\n"
        "after"
    )

    assert remove_placeholder_blocks(content) == "beforemiddleafter"


def test_remove_placeholder_blocks_leaves_bare_tokens() -> None:
    content = (
        "before <attachment attach_123> middle "
        f"{TABLE_PLACEHOLDER_TEMPLATE.format('table_456')} after"
    )

    assert remove_placeholder_blocks(content) == content
