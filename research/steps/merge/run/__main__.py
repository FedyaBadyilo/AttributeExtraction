"""Entrypoint: merge retrieval search hits into downstream context blocks.

Usage:
    python -m research.steps.merge.run
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
from research.steps.merge.domain.runner import run_merge
from research.steps.ocr.domain.models import SourceFile
from research.steps.retrieval.domain.models import AttributeSearchResult

logger = logging.getLogger(__name__)

RETRIEVAL_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "retrieval" / "output"
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
        search_path = RETRIEVAL_OUTPUT_DIR / f"{eos_id}_search.json"
        if not search_path.is_file():
            raise FileNotFoundError(f"Missing retrieval search output: {search_path}")

        search_rows = [
            AttributeSearchResult.model_validate(row)
            for row in json.loads(search_path.read_text(encoding="utf-8"))
        ]
        collection_name = config["QDRANT_COLLECTION_TEMPLATE"].format(eos_id=eos_id)

        logger.info(
            "[%d/%d] eos_id=%s  attrs=%d  collection=%s",
            i,
            total_eos,
            eos_id,
            len(search_rows),
            collection_name,
        )
        results = run_merge(search_rows, collection_name, config, qdrant=qdrant)
        out_path = OUTPUT_DIR / f"{eos_id}_merge.json"
        payload = [result.model_dump(mode="json") for result in results]
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        total_chunks = sum(len(result.merged_chunks) for result in results)
        logger.info(
            "Saved %d merge results (%d chunks) -> %s",
            len(results),
            total_chunks,
            out_path,
        )


if __name__ == "__main__":
    config_logger()
    main()
