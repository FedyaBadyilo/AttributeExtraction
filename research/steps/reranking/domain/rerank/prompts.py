"""Prompts, templates, and builders for LLM reranking."""

from __future__ import annotations

from research.steps.merge.domain.models import MergedChunk

SYSTEM_PROMPT = """# Role
You are an LLM reranker for technical specification extraction.

# Task
Score each provided chunk for one target attribute.

# Deterministic checklist (apply in order)
1) Attribute evidence:
- Check whether the chunk explicitly contains one of provided attribute names, or a clearly equivalent phrasing.
- If explicit evidence is absent, score must be <= 0.8.
2) Value linkage:
- Check whether the candidate value is explicitly linked to the target attribute in this same chunk.
- If value linkage is indirect, cross-row, cross-chunk, or inferred, score must be <= 0.8.
3) Unit consistency (if required):
- If unit in the chunk conflicts with allowed units, score must be <= 0.6.
4) Ambiguity control:
- If neighboring rows/fields can reasonably map to another attribute, treat as ambiguity and lower score.
5) Winner-takes-high:
- High confidence bands (>=0.9) are only for a unique best chunk.
- If two or more chunks are similarly strong, all of them must be <= 0.8.

# Scoring policy (0.0 to 1.0, step 0.1)
- 1.0: explicit attribute mention + explicit value linkage (+ correct unit if required), no ambiguity, unique best chunk.
- 0.9: same as 1.0 but with minor OCR/format noise; still unambiguous and unique best chunk.
- 0.7-0.8: strong relevance, but at least one limitation exists (non-exact wording OR minor ambiguity OR weaker value linkage).
- 0.5-0.6: partially relevant, notable ambiguity or only partial attribute-value correspondence.
- 0.3-0.4: weak thematic relation, no reliable attribute->value linkage.
- 0.0-0.2: irrelevant or clearly about another parameter.

# Rules
- Prefer exact matching to provided attribute names.
- If only a similar attribute/value appears and semantic equivalence is not explicit, score <= 0.6.
- If exact name match is absent, score must be <= 0.8.
- At most one chunk may have score >= 0.9.
- Use header_path only as a secondary signal of section suitability; it cannot raise score above 0.6 without explicit content evidence.
- Be conservative on ambiguity; choose lower score when uncertain.
- Return exactly one score item for each provided chunk number.
- If <unit_enum_list> is present in the attribute block, treat listed units as allowed; penalize chunks that imply a different unit.
"""

HINT_SCORING_INSTRUCTION = """\
- If <extraction_hint> is present, treat it as strict scope/exclusion guidance.
- If the chunk violates hint exclusions, score must be <= 0.4."""

EXECUTION_VARIANT_SCORING_INSTRUCTION = """\
- If <execution_variant> is present in the user prompt, prefer evidence for that execution option.
- Look for the execution option code in row/column labels or nearby text that distinguishes different values/tables.
- Chunks that only support a different execution option should receive a lower score."""

USER_PROMPT_TEMPLATE = """<attribute>
<names>{attr_name}</names>
<value_type>{value_type}</value_type>
{unit_block}{extraction_hint_block}</attribute>

<chunks>
{chunks_block}
</chunks>
"""

CHUNK_BLOCK_TEMPLATE = """\
<chunk number="{chunk_number}" file_priority="{file_priority}">
<header_path>{header_path}</header_path>
<content>
{content}
</content>
</chunk>"""

EXECUTION_VARIANT_SUPPLEMENT = """
<execution_variant>{execution_variant}</execution_variant>
"""


def build_system_prompt(
    *,
    include_extraction_hint: bool,
    include_execution_variant: bool = False,
) -> str:
    text = SYSTEM_PROMPT
    if include_extraction_hint:
        text += "\n" + HINT_SCORING_INSTRUCTION
    if include_execution_variant:
        text += "\n" + EXECUTION_VARIANT_SCORING_INSTRUCTION
    return text


def build_user_prompt(
    attr_name: str,
    value_type: str,
    unit_enum_list: list[str] | None,
    chunks: list[MergedChunk],
    execution_variant: str | None,
    extraction_hint: str | None = None,
    *,
    priority_by_point_id: dict[int, int],
) -> str:
    unit_block = ""
    if unit_enum_list:
        unit_block = f"<unit_enum_list>{', '.join(unit_enum_list)}</unit_enum_list>\n"

    extraction_hint_block = ""
    if extraction_hint:
        extraction_hint_block = f"<extraction_hint>{extraction_hint}</extraction_hint>\n"

    blocks: list[str] = []
    for i, c in enumerate(chunks, start=1):
        file_priority = priority_by_point_id.get(c.display_point_id, 0)
        blocks.append(
            CHUNK_BLOCK_TEMPLATE.format(
                chunk_number=i,
                file_priority=file_priority,
                header_path=" > ".join(c.header_path),
                content=c.content,
            )
        )
    prompt = USER_PROMPT_TEMPLATE.format(
        attr_name=attr_name,
        value_type=value_type,
        unit_block=unit_block,
        extraction_hint_block=extraction_hint_block,
        chunks_block="\n\n".join(blocks),
    )
    if execution_variant:
        prompt += EXECUTION_VARIANT_SUPPLEMENT.format(execution_variant=execution_variant)
    return prompt
