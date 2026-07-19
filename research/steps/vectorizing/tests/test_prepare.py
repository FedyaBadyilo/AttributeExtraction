from research.steps.vectorizing.domain.prepare import (
    prepare_content_for_indexing,
    strip_markdown_for_indexing,
)


def test_prepare_content_strips_markdown_and_adds_header_path() -> None:
    content = '# **1. Раздел**\nТекст\n<table_ref uid="1"/>\n\n и **жирный**.'
    result = prepare_content_for_indexing(content, ["Титульный лист", "1. Раздел"])
    assert result.startswith("[Титульный лист -> 1. Раздел]\n")
    assert "table_ref" not in result
    assert "**" not in result
    assert "жирный" in result


def test_prepare_content_empty_header_path() -> None:
    result = prepare_content_for_indexing("plain", [])
    assert result == "[]\nplain"


def test_strip_markdown_for_indexing_removes_full_placeholder_blocks() -> None:
    content = (
        "\n<attachment attach_c60cc382-e522-4a37-ba86-8f735ce0f88a>\n\n"
        "\n<attachment attach_848fcf06-1848-4320-b859-4aeb1829c27c>\n\n"
    )

    assert strip_markdown_for_indexing(content) == ""


def test_strip_markdown_for_indexing_leaves_bare_placeholder() -> None:
    content = "before <attachment attach_123> after"

    assert strip_markdown_for_indexing(content) == content


def test_strip_markdown_for_indexing_extracts_html_table_cell_text() -> None:
    content = (
        "<table>"
        '<tr><td rowspan="2">A&amp;B</td><td>c</td></tr>'
        "<tr><td>d &lt; e</td></tr>"
        "</table>"
    )

    assert strip_markdown_for_indexing(content) == "A&B c\nd < e"


def test_prepare_content_indexes_table_cells_only() -> None:
    content = (
        "<table>"
        "<tr><td>col1</td><td>col2</td></tr>"
        "<tr><td>a</td><td>b</td></tr>"
        "</table>"
    )
    result = prepare_content_for_indexing(content, ["Section"])

    assert result == "[Section]\ncol1 col2\na b"
    assert "<table" not in result
    assert "rowspan" not in result
