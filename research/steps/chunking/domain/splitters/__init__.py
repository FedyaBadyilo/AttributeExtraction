"""Splitters for structure and table chunks.

Token count uses the embedder HuggingFace tokenizer (same model as ``EMBEDDINGS``).
Structure text is split by separators; tables by HTML rows with header repeated in each part.
Oversized rowspan atoms escalate: mid-span row partition, then mid-cell text split,
then mid-cols when a row skeleton is wider than the budget.
"""

from research.steps.chunking.domain.splitters.structure import (
    STRUCTURE_SEPARATORS,
    split_structure_text,
)
from research.steps.chunking.domain.splitters.table import TableSplitPart, split_table_html
from research.steps.chunking.domain.splitters.tokens import make_token_count_fn

__all__ = [
    "STRUCTURE_SEPARATORS",
    "TableSplitPart",
    "make_token_count_fn",
    "split_structure_text",
    "split_table_html",
]
