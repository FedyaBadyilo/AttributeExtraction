from __future__ import annotations

import json
from pathlib import Path


def write_examples_manifest(path: Path, examples: list[dict]) -> None:
    payload = [
        {
            "eos_id": example["eos_id"],
            "pdf_filename": example["pdf_filename"],
            "file_priority": example["file_priority"],
            "variant_execution_id": example["variant_execution_id"],
            "class_code": example["class_code"],
        }
        for example in examples
    ]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_class_attribute_sets(path: Path, class_attribute_sets: dict[str, list[dict]]) -> None:
    path.write_text(
        json.dumps(class_attribute_sets, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_ground_truth(path: Path, ground_truth_rows: list[dict]) -> None:
    lines = [json.dumps(row, ensure_ascii=False) for row in ground_truth_rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
