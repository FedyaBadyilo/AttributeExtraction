"""Convert backend catalog seed → research.steps attribute models."""

from __future__ import annotations

from research.steps.attribute_grouping.domain.models import (
    AttributeGroup,
    AttributeGroups,
    ClassAttribute,
    ClassAttributeSet,
)

from backend.app.catalog.models import AttributeGroupingPlanDocument, AttributesSet


def to_class_attribute_set(catalog: AttributesSet, class_code: str) -> ClassAttributeSet:
    """Map seed catalog to ClassAttributeSet (extraction-only attributes)."""
    attributes: dict[str, ClassAttribute] = {}
    for attr_id, item in catalog.attributes.items():
        if not item.for_extraction:
            continue
        descr_parts: list[str] = []
        if item.description:
            descr_parts.append(item.description)
        if item.extraction_hint:
            descr_parts.append(item.extraction_hint)
        if item.rag_hint:
            descr_parts.append(item.rag_hint)
        if item.altnames:
            descr_parts.append("Также: " + "; ".join(item.altnames))
        attributes[attr_id] = ClassAttribute(
            attr_id=attr_id,
            attr_name=item.attribute_name,
            descr="\n".join(descr_parts) or None,
            attr_type=item.value_type,
            for_extraction=True,
            units=item.unit_enum_list,
            allowed_values=item.enum_list,
        )
    return ClassAttributeSet(class_code=class_code, attributes=attributes)


def to_attribute_groups(plan: AttributeGroupingPlanDocument) -> AttributeGroups:
    groups = [
        AttributeGroup(attr_ids=list(group.attribute_ids))
        for group in plan.semantic_groups
        if group.attribute_ids
    ]
    return AttributeGroups(groups=groups)
