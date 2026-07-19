from __future__ import annotations

from research.steps.attribute_grouping.domain.models import ClassAttribute
from research.steps.common.downstream_text import remove_placeholder_blocks
from research.steps.merge.domain.models import MergedChunk

SYSTEM_INSTRUCTION = """# Role
You are an attribute extraction system for technical specification documents (ТЗ).

# Task
You will receive a group of related attributes sharing a common document context.

# Rules
**Use the provided context chunks as the only source of truth.**

## Matching & selection
- **Match by label:** prefer **exact** label match; use close synonyms only if they denote the **same concept** (not a proxy; not broader/narrower).
- **Competitive assignment:** if the same candidate could fit multiple attributes, assign it only to the attribute whose label match is **most precise**; all others must be **null**.
- **No double-assign:** never assign the same candidate/value to two different attributes.

**Null safety:** Each attribute is independent — the fact that neighboring attributes have values \
does not mean this one does too. If no source label matches this attribute's names, return null. \
Extracting null is **always safer** than assigning a value to the wrong attribute.

# Table format
Tables are HTML with `rowspan` / `colspan`.
**Quote from tables:** if the answer is a single cell, quote its text only; if it spans several cells, you may quote an HTML fragment that keeps the relevant tags.
"""

EXECUTION_VARIANT_SYSTEM_SUPPLEMENT = """
# Execution option
Within the framework of this ТЗ, some attributes may have several **different** values, depending on the execution option. \
In this case, use the value belonging to the option provided in the user prompt under `<execution_variant>`. \
Look for this code in a row/column of the table or in text fragments near different values/tables.
"""

EXECUTION_VARIANT_USER_TEMPLATE = """
<execution_variant>{execution_variant}</execution_variant>
"""

HINT_EXTRACTION_INSTRUCTION = """\
## Extraction hints
Some attributes include `<extraction_hint>` tags. Use them to determine the correct scope, object, and value format, and to exclude values that belong to other attributes."""

USER_PROMPT_TEMPLATE = """\
<attributes>
{attributes_block}
</attributes>
<context>
{context}
</context>"""

_ATTRIBUTE_BLOCK_TEMPLATE = """\
<attribute index="{index}">
<names>{names}</names>
{hint_block}</attribute>"""

CHUNK_BLOCK_TEMPLATE = """\
<chunk number="{chunk_number}" file_priority="{file_priority}">
<header_path>{header_path}</header_path>
{content}
</chunk>"""


def build_system_prompt(
    *,
    include_execution_variant: bool,
    has_hints: bool,
) -> str:
    base = SYSTEM_INSTRUCTION.strip()
    if has_hints:
        base += "\n\n" + HINT_EXTRACTION_INSTRUCTION
    if include_execution_variant:
        base += "\n" + EXECUTION_VARIANT_SYSTEM_SUPPLEMENT
    return base


def _build_attribute_block(index: int, attribute: ClassAttribute) -> str:
    hint_block = ""
    if attribute.descr:
        hint_block = f"<extraction_hint>{attribute.descr}</extraction_hint>\n"
    return _ATTRIBUTE_BLOCK_TEMPLATE.format(
        index=index,
        names=attribute.attr_name,
        hint_block=hint_block,
    )


def _format_context(
    chunks: list[MergedChunk],
    *,
    priority_by_point_id: dict[int, int],
) -> str:
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        file_priority = priority_by_point_id.get(chunk.display_point_id, 0)
        header_path_str = " > ".join(chunk.header_path)
        content = remove_placeholder_blocks(chunk.content)
        parts.append(
            CHUNK_BLOCK_TEMPLATE.format(
                chunk_number=i,
                file_priority=file_priority,
                header_path=header_path_str,
                content=content,
            )
        )
    return "\n\n".join(parts)


def build_user_prompt(
    group_attr_items: list[tuple[int, ClassAttribute]],
    context: str,
    *,
    execution_variant: str | None,
) -> str:
    attributes_block = "\n".join(
        _build_attribute_block(idx, attr) for idx, attr in group_attr_items
    )
    user_prompt = USER_PROMPT_TEMPLATE.format(
        attributes_block=attributes_block,
        context=context,
    ).strip()
    if execution_variant:
        user_prompt += EXECUTION_VARIANT_USER_TEMPLATE.format(execution_variant=execution_variant)
    return user_prompt
