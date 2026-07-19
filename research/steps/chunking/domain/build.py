"""Chunk emission from FormattedDocument: recursive walk over structure.

Accumulate headers (level_1=1) and list items (level_1=2) until body; on body emit one structure
chunk and one chunk per table (subject to min_chunk_tokens). Structure chunks and table chunks are
independent; each table is a separate chunk. Long chunks are split by max_chunk_tokens (structure by
separators, HTML tables by rowspan-safe rows / mid-span / mid-cell / mid-cols with ``seam_to_next``).
"""

from __future__ import annotations

import re
from collections.abc import Callable

from research.steps.chunking.domain.models import (
    ROOT_HEADER_LABEL,
    Chunk,
    StructureChunkMetadata,
    TableChunkMetadata,
)
from research.steps.chunking.domain.splitters import split_structure_text, split_table_html
from research.steps.markdown_formatting.domain.models import (
    FormattedDocument,
    FormattedNode,
    FormattedNodeMetadata,
)
from research.steps.markdown_formatting.domain.structure.annotations.processors.attach.processor import (
    ATTACH_PLACEHOLDER_TEMPLATE,
)
from research.steps.markdown_formatting.domain.structure.annotations.processors.bold.processor import BOLD_WRAPPER
from research.steps.markdown_formatting.domain.structure.annotations.processors.italic.processor import ITALIC_WRAPPER
from research.steps.markdown_formatting.domain.structure.annotations.processors.linked_text.processor import (
    LINKED_CLOSE,
    LINKED_OPEN,
)
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
)
from research.steps.markdown_formatting.domain.structure.header_levels import is_header_type, is_list_type
from research.steps.markdown_formatting.domain.structure.node_formatter import HEADER_PREFIX_CHAR

_TITLE_STRIP_CHARS = set(
    HEADER_PREFIX_CHAR + BOLD_WRAPPER + ITALIC_WRAPPER + LINKED_OPEN + LINKED_CLOSE + "\n "
)

_TABLE_UID_PATTERN = re.compile(
    re.escape(TABLE_PLACEHOLDER_TEMPLATE).replace(re.escape("{}"), r'([^"]+)')
)


def _table_uids_in_content(content: str) -> list[str]:
    """Return table uids whose placeholders appear in content, in document order."""
    seen: set[str] = set()
    result: list[str] = []
    for uid in _TABLE_UID_PATTERN.findall(content):
        if uid not in seen:
            seen.add(uid)
            result.append(uid)
    return result


def strip_header_line_to_clean_title(markdown_header_line: str) -> str:
    """Strip header markdown to a clean title for ``header_path`` metadata."""
    if not markdown_header_line:
        return ""

    attach_bare = re.escape(ATTACH_PLACEHOLDER_TEMPLATE).replace("\\{\\}", "[^>]+")
    table_bare = re.escape(TABLE_PLACEHOLDER_TEMPLATE).replace("\\{\\}", r'[^"]+')

    text = markdown_header_line
    text = re.sub(attach_bare, "", text)
    text = re.sub(table_bare, "", text)

    text = text.strip()
    while text and text[0] in _TITLE_STRIP_CHARS:
        text = text[1:]
    while text and text[-1] in _TITLE_STRIP_CHARS:
        text = text[:-1]
    return text.strip()


def _table_html_by_uid(document: FormattedDocument) -> dict[str, str]:
    return {table.uid: table.html for table in document.tables}


def _get_table_uids(metadata: FormattedNodeMetadata) -> list[str]:
    tables = getattr(metadata, "tables", None)
    if not tables:
        return []
    return [str(uid) for uid in tables]


class ChunkWalkerState:
    """Mutable state for the structure tree walk."""

    def __init__(
        self,
        *,
        max_chunk_tokens: int,
        min_chunk_tokens: int,
        token_count_fn: Callable[[str], int],
        file_name: str = "",
    ) -> None:
        self.text_buffer: list[str] = []
        self.table_uids: list[str] = []
        self.page_numbers: list[int] = []
        self.header_path: list[str] = []
        self._path_snapshot: list[str] = [ROOT_HEADER_LABEL]
        self.document_chunk_index = 0
        self.chunks: list[Chunk] = []
        self.max_chunk_tokens = max_chunk_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.token_count_fn = token_count_fn
        self.last_was_body = False
        self.file_name = file_name

    def append_text(self, text: str) -> None:
        if text:
            self.text_buffer.append(text)
            self._path_snapshot = list(self.header_path) if self.header_path else [ROOT_HEADER_LABEL]

    def append_table_uids(self, uids: list[str]) -> None:
        self.table_uids.extend(uids)

    def append_page(self, page_id: int) -> None:
        self.page_numbers.append(page_id)

    def emit_structure_chunk(self) -> None:
        combined = "".join(self.text_buffer)
        page_numbers = sorted(set(self.page_numbers)) if self.page_numbers else None
        header_path = self._path_snapshot
        if self.token_count_fn(combined) <= self.max_chunk_tokens:
            self.chunks.append(
                Chunk(
                    content=combined,
                    metadata=StructureChunkMetadata(
                        document_chunk_index=self.document_chunk_index,
                        page_numbers=page_numbers,
                        table_uids=_table_uids_in_content(combined),
                        header_path=header_path,
                        file_name=self.file_name,
                    ),
                )
            )
            self.document_chunk_index += 1
        else:
            for part in split_structure_text(combined, self.max_chunk_tokens, self.token_count_fn):
                self.chunks.append(
                    Chunk(
                        content=part,
                        metadata=StructureChunkMetadata(
                            document_chunk_index=self.document_chunk_index,
                            page_numbers=page_numbers,
                            table_uids=_table_uids_in_content(part),
                            header_path=header_path,
                            file_name=self.file_name,
                        ),
                    )
                )
                self.document_chunk_index += 1
        self.text_buffer.clear()
        self.page_numbers.clear()

    def emit_table_chunks(self, table_html_by_uid: dict[str, str]) -> None:
        uids = list(self.table_uids)
        self.table_uids.clear()
        header_path = self._path_snapshot
        for uid in uids:
            html = table_html_by_uid.get(uid, "")
            parts = split_table_html(
                html,
                self.max_chunk_tokens,
                self.token_count_fn,
                table_uid=uid,
            )
            for table_chunk_index, part in enumerate(parts):
                self.chunks.append(
                    Chunk(
                        content=part.content,
                        metadata=TableChunkMetadata(
                            document_chunk_index=self.document_chunk_index,
                            table_uid=uid,
                            table_chunk_index=table_chunk_index,
                            seam_to_next=part.seam_to_next,
                            header_path=header_path,
                            file_name=self.file_name,
                        ),
                    )
                )
                self.document_chunk_index += 1


def _walk(
    node: FormattedNode,
    state: ChunkWalkerState,
    table_html_by_uid: dict[str, str],
) -> None:
    metadata = node.metadata
    paragraph_type = metadata.paragraph_type
    text = node.text

    if state.text_buffer and is_header_type(paragraph_type) and state.last_was_body:
        state.emit_structure_chunk()
        state.emit_table_chunks(table_html_by_uid)

    if is_header_type(paragraph_type):
        title = strip_header_line_to_clean_title(text)
        if title:
            state.header_path.append(title)

    state.append_text(text)
    state.append_table_uids(_get_table_uids(metadata))
    state.append_page(metadata.page_id)
    state.last_was_body = not (is_header_type(paragraph_type) or is_list_type(paragraph_type))

    if not is_header_type(paragraph_type) and not is_list_type(paragraph_type):
        if any(part.strip() for part in state.text_buffer):
            token_count = state.token_count_fn("".join(state.text_buffer))
            if state.min_chunk_tokens == 0 or token_count >= state.min_chunk_tokens:
                state.emit_structure_chunk()
                state.emit_table_chunks(table_html_by_uid)

    for sub in node.subparagraphs:
        _walk(sub, state, table_html_by_uid)

    if is_header_type(paragraph_type):
        title = strip_header_line_to_clean_title(text)
        if title:
            state.header_path.pop()


def build_chunks(
    document: FormattedDocument,
    *,
    max_chunk_tokens: int,
    min_chunk_tokens: int,
    token_count_fn: Callable[[str], int],
    file_name: str = "",
) -> list[Chunk]:
    """Walk ``document.structure`` in document order and emit structure/table chunks."""
    table_html_by_uid = _table_html_by_uid(document)
    state = ChunkWalkerState(
        max_chunk_tokens=max_chunk_tokens,
        min_chunk_tokens=min_chunk_tokens,
        token_count_fn=token_count_fn,
        file_name=file_name,
    )
    _walk(document.structure, state, table_html_by_uid)
    if state.text_buffer:
        state.emit_structure_chunk()
    state.emit_table_chunks(table_html_by_uid)
    return state.chunks
