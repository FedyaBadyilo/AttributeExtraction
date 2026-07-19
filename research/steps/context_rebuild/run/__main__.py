"""Entrypoint: rebuild final grouped extraction context per eos_id.

Usage:
    python -m research.steps.context_rebuild.run
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

from infra.config import get_config_and_env
from infra.config.loader import config_logger
from infra.qdrant import get_qdrant_client
from research.datasets.access import load_examples_manifest
from research.steps.attribute_grouping.domain.models import AttributeGroups
from research.steps.context_rebuild.domain import rebuild_grouped_context
from research.steps.merge.domain.models import MergeResult
from research.steps.ocr.domain.models import SourceFile
from research.steps.reranking.domain.models import RerankAttribute

logger = logging.getLogger(__name__)

CONTEXT_GROUPING_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "context_grouping" / "output"
MERGE_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "merge" / "output"
RERANKING_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "reranking" / "output"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def main() -> None:
    config = get_config_and_env()
    qdrant = get_qdrant_client(config)
    source_files = [SourceFile.model_validate(e) for e in load_examples_manifest()]

    by_eos_id: dict[int, list[SourceFile]] = defaultdict(list)
    for sf in source_files:
        by_eos_id[sf.eos_id].append(sf)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    eos_ids = sorted(by_eos_id)
    total_eos = len(eos_ids)

    for i, eos_id in enumerate(eos_ids, start=1):
        groups_path = CONTEXT_GROUPING_OUTPUT_DIR / f"{eos_id}_attribute_groups.json"
        if not groups_path.is_file():
            raise FileNotFoundError(f"Missing context grouping output: {groups_path}")
        attr_groups = AttributeGroups.model_validate_json(groups_path.read_text(encoding="utf-8"))

        rerank_path = RERANKING_OUTPUT_DIR / f"{eos_id}_rerank.json"
        if not rerank_path.is_file():
            raise FileNotFoundError(f"Missing rerank output: {rerank_path}")
        rerank_result = [
            RerankAttribute.model_validate(row)
            for row in json.loads(rerank_path.read_text(encoding="utf-8"))
        ]

        merge_path = MERGE_OUTPUT_DIR / f"{eos_id}_merge.json"
        if not merge_path.is_file():
            raise FileNotFoundError(f"Missing merge output: {merge_path}")
        merge_results = [
            MergeResult.model_validate(row)
            for row in json.loads(merge_path.read_text(encoding="utf-8"))
        ]

        collection_name = config["QDRANT_COLLECTION_TEMPLATE"].format(eos_id=eos_id)
        logger.info(
            "[%d/%d] eos_id=%s  groups=%d  rerank_attrs=%d",
            i,
            total_eos,
            eos_id,
            len(attr_groups.groups),
            len(rerank_result),
        )
        result = rebuild_grouped_context(
            attr_groups,
            rerank_result,
            merge_results,
            qdrant,
            collection_name,
        )

        out_path = OUTPUT_DIR / f"{eos_id}_extraction_context.json"
        out_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        logger.info(
            "Saved extraction context: %d groups, %d attrs -> %s",
            len(result.groups),
            len(result.rerank_result),
            out_path,
        )


if __name__ == "__main__":
    config_logger()
    main()
