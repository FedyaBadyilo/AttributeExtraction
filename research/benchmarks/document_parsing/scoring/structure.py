"""Structure-only metrics parsed symmetrically from canonical Markdown."""

from __future__ import annotations

import re

from apted import APTED, Config
from pydantic import BaseModel, ConfigDict, Field

from research.benchmarks.document_parsing.canonicalize import (
    HtmlTable,
    canonicalize_pair,
    normalize_inline_text,
    parse_html_tables,
)
from research.benchmarks.document_parsing.scoring.models import (
    CountComparison,
    SequenceScores,
    StructuralCountScores,
    StructureScores,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_LIST_RE = re.compile(r"^(\s*)([-+*]|(?:\d+\.)+\d*|\d+\))\s+(.+)$")


class _AstNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    children: list["_AstNode"] = Field(default_factory=list)


class _AstConfig(Config):
    def children(self, node: _AstNode) -> list[_AstNode]:
        return node.children

    def rename(self, node1: _AstNode, node2: _AstNode) -> int:
        return int(node1.label != node2.label)


def _comparison(pred: int, gt: int) -> CountComparison:
    maximum = max(pred, gt)
    similarity = min(pred, gt) / maximum if maximum else 1.0
    return CountComparison(pred=pred, gt=gt, delta=pred - gt, similarity=similarity)


def _headings(markdown: str) -> list[tuple[int, str]]:
    table_lines: set[int] = set()
    for table in parse_html_tables(markdown):
        table_lines.update(range(table.start_line, table.end_line))
    result: list[tuple[int, str]] = []
    for line_number, line in enumerate(markdown.splitlines()):
        if line_number in table_lines:
            continue
        match = _HEADING_RE.fullmatch(line.strip())
        if match:
            result.append((len(match.group(1)), normalize_inline_text(match.group(2))))
    return result


def _lcs_length(left: list[tuple[int, str]], right: list[tuple[int, str]]) -> int:
    previous = [0] * (len(right) + 1)
    for left_item in left:
        current = [0]
        for index, right_item in enumerate(right, start=1):
            if left_item == right_item:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]


def _sequence_scores(
    pred: list[tuple[int, str]],
    gt: list[tuple[int, str]],
) -> SequenceScores:
    lcs = _lcs_length(pred, gt)
    if not pred and not gt:
        precision = recall = f1 = 1.0
    else:
        precision = lcs / len(pred) if pred else 0.0
        recall = lcs / len(gt) if gt else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return SequenceScores(
        pred_count=len(pred),
        gt_count=len(gt),
        lcs_length=lcs,
        precision=precision,
        recall=recall,
        f1=f1,
    )


def _append_table_ast(parent: _AstNode, table: HtmlTable) -> None:
    table_node = _AstNode(label="table")
    for row in table.rows:
        row_node = _AstNode(label="row:body")
        for cell in row:
            row_node.children.append(
                _AstNode(label=f"column:{cell.rowspan}x{cell.colspan}")
            )
        table_node.children.append(row_node)
    parent.children.append(table_node)


def _append_list_ast(parent: _AstNode, items: list[tuple[int, bool]]) -> None:
    first_indent, first_ordered = items[0]
    root_list = _AstNode(label=f"list:{'ordered' if first_ordered else 'unordered'}")
    parent.children.append(root_list)
    stack: list[tuple[int, _AstNode]] = [(first_indent, root_list)]
    last_item: _AstNode | None = None

    for indent, ordered in items:
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()
        if indent > stack[-1][0]:
            if last_item is None:
                raise ValueError("Nested list item has no parent item")
            nested = _AstNode(label=f"list:{'ordered' if ordered else 'unordered'}")
            last_item.children.append(nested)
            stack.append((indent, nested))
        item = _AstNode(label="list_item")
        stack[-1][1].children.append(item)
        last_item = item


def _build_ast(markdown: str) -> _AstNode:
    lines = markdown.splitlines()
    tables = parse_html_tables(markdown)
    table_by_start = {table.start_line: table for table in tables}
    root = _AstNode(label="document")
    heading_stack: list[tuple[int, _AstNode]] = []

    def container() -> _AstNode:
        return heading_stack[-1][1] if heading_stack else root

    index = 0
    while index < len(lines):
        table = table_by_start.get(index)
        if table is not None:
            _append_table_ast(container(), table)
            index = table.end_line
            continue

        line = lines[index]
        if not line.strip():
            index += 1
            continue

        heading = _HEADING_RE.fullmatch(line.strip())
        if heading:
            level = len(heading.group(1))
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            node = _AstNode(label=f"heading:{level}")
            container().children.append(node)
            heading_stack.append((level, node))
            index += 1
            continue

        list_match = _LIST_RE.fullmatch(line)
        if list_match:
            items: list[tuple[int, bool]] = []
            while index < len(lines):
                current = _LIST_RE.fullmatch(lines[index])
                if current is None:
                    break
                marker = current.group(2)
                items.append((len(current.group(1).expandtabs(4)), marker[0].isdigit()))
                index += 1
            _append_list_ast(container(), items)
            continue

        index += 1
        while index < len(lines):
            if not lines[index].strip() or index in table_by_start:
                break
            if _HEADING_RE.fullmatch(lines[index].strip()) or _LIST_RE.fullmatch(lines[index]):
                break
            index += 1
        container().children.append(_AstNode(label="paragraph"))

    return root


def _node_count(node: _AstNode) -> int:
    return 1 + sum(_node_count(child) for child in node.children)


def _ast_similarity(pred_markdown: str, gt_markdown: str) -> float:
    pred_tree = _build_ast(pred_markdown)
    gt_tree = _build_ast(gt_markdown)
    distance = APTED(pred_tree, gt_tree, _AstConfig()).compute_edit_distance()
    denominator = max(_node_count(pred_tree), _node_count(gt_tree))
    return max(0.0, min(1.0, 1.0 - float(distance) / denominator))


def score_structure(pred_markdown: str, gt_markdown: str) -> StructureScores:
    """Score counts, heading order, and structure-only Markdown AST similarity."""
    canonical_pred, canonical_gt = canonicalize_pair(pred_markdown, gt_markdown)
    pred_headings = _headings(canonical_pred)
    gt_headings = _headings(canonical_gt)
    heading_levels = {
        level: _comparison(
            sum(item_level == level for item_level, _ in pred_headings),
            sum(item_level == level for item_level, _ in gt_headings),
        )
        for level in range(1, 7)
    }

    pred_tables = parse_html_tables(canonical_pred)
    gt_tables = parse_html_tables(canonical_gt)
    table_blocks = _comparison(len(pred_tables), len(gt_tables))
    data_rows = _comparison(
        sum(table.data_row_count for table in pred_tables),
        sum(table.data_row_count for table in gt_tables),
    )
    count_components = [*heading_levels.values(), table_blocks, data_rows]
    counts = StructuralCountScores(
        heading_levels=heading_levels,
        table_blocks=table_blocks,
        data_rows=data_rows,
        similarity=sum(item.similarity for item in count_components) / len(count_components),
    )
    return StructureScores(
        counts=counts,
        headings=_sequence_scores(pred_headings, gt_headings),
        ast_similarity=_ast_similarity(canonical_pred, canonical_gt),
    )
