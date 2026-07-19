"""Structure-text splitting by separator hierarchy."""

from __future__ import annotations

from collections.abc import Callable

from langchain_text_splitters import RecursiveCharacterTextSplitter

STRUCTURE_SEPARATORS = [
    ".\n\n",
    ";\n\n",
    "\n\n",
    ".\n",
    ";\n",
    "\n",
    ". ",
    "; ",
    " ",
]


def split_structure_text(
    text: str,
    max_tokens: int,
    length_function: Callable[[str], int],
) -> list[str]:
    """Split structure text by separator hierarchy; size measured in tokens."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_tokens,
        chunk_overlap=0,
        separators=STRUCTURE_SEPARATORS,
        keep_separator="end",
        length_function=length_function,
    )
    return splitter.split_text(text)
