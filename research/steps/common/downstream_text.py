"""Remove inserted placeholder blocks from text."""

from __future__ import annotations

import re

from research.steps.markdown_formatting.domain.structure.annotations.processors.attach.processor import (
    ATTACH_PLACEHOLDER_TEMPLATE,
    ATTACH_PREFIX,
    ATTACH_SUFFIX,
)
from research.steps.markdown_formatting.domain.structure.annotations.processors.table.processor import (
    TABLE_PLACEHOLDER_TEMPLATE,
    TABLE_PREFIX,
    TABLE_SUFFIX,
)

ATTACH_BLOCK_TEMPLATE = ATTACH_PREFIX + ATTACH_PLACEHOLDER_TEMPLATE + ATTACH_SUFFIX
TABLE_BLOCK_TEMPLATE = TABLE_PREFIX + TABLE_PLACEHOLDER_TEMPLATE + TABLE_SUFFIX


def _block_re(block_template: str, *, uid_pattern: str = r"[^\s>]+") -> re.Pattern[str]:
    pattern = re.escape(block_template).replace(re.escape("{}"), uid_pattern)
    return re.compile(pattern)


_ATTACH_BLOCK_RE = _block_re(ATTACH_BLOCK_TEMPLATE)
_TABLE_BLOCK_RE = _block_re(TABLE_BLOCK_TEMPLATE, uid_pattern=r'[^"]+')


def remove_placeholder_blocks(content: str) -> str:
    """Remove full attachment and table placeholder blocks inserted by markdown_formatting."""
    content = _ATTACH_BLOCK_RE.sub("", content)
    return _TABLE_BLOCK_RE.sub("", content)
