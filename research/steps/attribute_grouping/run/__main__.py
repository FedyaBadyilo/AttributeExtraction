from __future__ import annotations

import json
import logging
from pathlib import Path

from infra.config.loader import config_logger
from research.datasets.access import load_class_attribute_sets
from research.steps.attribute_grouping.domain.grouping import run_grouping
from research.steps.attribute_grouping.domain.models import ClassAttribute, ClassAttributeSet

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
OUTPUT_FILENAME = "attribute_groups.json"
_CLASS_ATTR_FIELDS = frozenset(ClassAttribute.model_fields)


def _to_class_attribute(raw: dict) -> ClassAttribute:
    return ClassAttribute.model_validate({k: raw[k] for k in _CLASS_ATTR_FIELDS})


def main() -> None:
    config_logger()
    raw_sets = load_class_attribute_sets()
    OUTPUT_DIR.mkdir(exist_ok=True)

    by_class: dict[str, dict] = {}
    for class_code, raw_attrs in raw_sets.items():
        logger.info("Processing class %s — %d attrs", class_code, len(raw_attrs))
        attrs = {
            a.attr_id: a
            for raw in raw_attrs
            if (a := _to_class_attribute(raw)).for_extraction
        }
        logger.info("  for_extraction: %d", len(attrs))
        attr_set = ClassAttributeSet(class_code=class_code, attributes=attrs)
        result = run_grouping(attr_set)
        logger.info("  groups: %d", len(result.groups))
        by_class[class_code] = result.model_dump(mode="json")

    output_path = OUTPUT_DIR / OUTPUT_FILENAME
    output_path.write_text(
        json.dumps(by_class, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("Written %d classes -> %s", len(by_class), output_path)


if __name__ == "__main__":
    main()
