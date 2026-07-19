from __future__ import annotations

from research.steps.attribute_grouping.domain.models import ClassAttribute

SYSTEM_PROMPT_TEMPLATE: str = """\
## Role
You are designing grouping for joint attribute extraction from technical documents. \
Your output is used to decide which attributes are extracted together in one model call.

## Task
You are given attributes (id, name, type, optional description). \
Return only multi-attribute groups of size {min_group_size}..{max_group_size}.

## Goal
Build semantically coherent groups that reduce value confusion during extraction.

## Principles
- Group by confusion risk first, not by table proximity alone.
- Group attributes that describe the same semantic area and are likely to be interpreted together.
- Consider not only local co-occurrence, but also meaning compatibility.
- Keep apart attributes with different semantic roles even if they can appear in the same section.
- Prefer groups with consistent interpretation axis (for example: variants of one concept).
- Prefer cleaner groups over larger mixed groups.

If a grouping decision is uncertain, avoid forcing a mixed group."""


def build_system_prompt(min_group_size: int, max_group_size: int) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        min_group_size=min_group_size, max_group_size=max_group_size
    )


def format_attrs_for_prompt(
    partition_attr_ids: list[str],
    attrs_by_id: dict[str, ClassAttribute],
) -> str:
    lines: list[str] = []
    for aid in partition_attr_ids:
        attr = attrs_by_id[aid]
        descr_line = ""
        if attr.descr is not None:
            descr_line = f"\n  <description>{attr.descr}</description>"
        lines.append(
            f'<attribute id="{aid}">\n'
            f"  <name>{attr.attr_name}</name>\n"
            f"  <type>{attr.attr_type.value}</type>"
            f"{descr_line}\n"
            f"</attribute>"
        )
    return "\n".join(lines)
