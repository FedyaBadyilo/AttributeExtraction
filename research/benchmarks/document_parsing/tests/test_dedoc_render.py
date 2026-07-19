from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from research.benchmarks.document_parsing.pipelines.dedoc import (
    render_formatted_document,
    run_dedoc_pipeline,
)
from research.steps.markdown_formatting.domain.models import (
    FormattedDocument,
    FormattedNode,
    FormattedNodeMetadata,
    FormattedTable,
)


def _node(
    node_id: str,
    text: str,
    children: list[FormattedNode] | None = None,
) -> FormattedNode:
    return FormattedNode(
        node_id=node_id,
        text=text,
        metadata=FormattedNodeMetadata(page_id=0),
        subparagraphs=children or [],
    )


def test_render_uses_dfs_substitutes_tables_and_strips_attachments() -> None:
    document = FormattedDocument(
        structure=_node(
            "root",
            "root\n",
            [
                _node(
                    "first",
                    'before\n<table_ref uid="table-1"/>\nafter\n<attachment image.png>\n',
                    [_node("nested", "nested\n")],
                ),
                _node("second", "second\n"),
            ],
        ),
        tables=[FormattedTable(uid="table-1", html="| A |\n| - |\n| B |")],
    )

    assert render_formatted_document(document) == (
        "root\nbefore\n| A |\n| - |\n| B |\nafter\n\nnested\nsecond\n"
    )


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (
            FormattedDocument(
                structure=_node("root", '<table_ref uid="missing"/>'),
                tables=[],
            ),
            "unresolved table ID",
        ),
        (
            FormattedDocument(
                structure=_node(
                    "root",
                    '<table_ref uid="t"/><table_ref uid="t"/>',
                ),
                tables=[FormattedTable(uid="t", html="table")],
            ),
            "duplicate table placeholder",
        ),
        (
            FormattedDocument(
                structure=_node("root", "text"),
                tables=[FormattedTable(uid="t", html="table")],
            ),
            "orphan sidecar table",
        ),
        (
            FormattedDocument(
                structure=_node("root", '<table_ref uid="t"/>'),
                tables=[
                    FormattedTable(uid="t", html="one"),
                    FormattedTable(uid="t", html="two"),
                ],
            ),
            "duplicate sidecar table",
        ),
    ],
)
def test_render_rejects_broken_table_id_invariants(
    document: FormattedDocument, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        render_formatted_document(document)


class _FakeParsed(BaseModel):
    content: dict[str, str]


def test_pipeline_uses_injected_converter_and_formatter_without_real_ocr(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def converter(**kwargs: object) -> _FakeParsed:
        calls.append("convert")
        assert kwargs["file_path"] == tmp_path / "input.pdf"
        assert kwargs["output_dir"] == tmp_path / "work"
        return _FakeParsed(content={"text": "source"})

    def formatter(content: object) -> FormattedDocument:
        calls.append("format")
        assert content == {"text": "source"}
        return FormattedDocument(
            structure=_node("root", "prediction"),
            tables=[],
        )

    parsed, formatted, prediction = run_dedoc_pipeline(
        tmp_path / "input.pdf",
        tmp_path / "work",
        config={"OCR": {"on_gpu": False}},
        converter=converter,
        formatter=formatter,
    )

    assert calls == ["convert", "format"]
    assert parsed.content == {"text": "source"}
    assert formatted.structure.node_id == "root"
    assert prediction == "prediction"
