"""Load processed dataset artifacts as raw JSON structures.
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Demo/research processed artifacts for step debug runs.
PROCESSED_DIR = Path(__file__).resolve().parent / "processed"
EXAMPLES_MANIFEST_FILENAME = "examples_manifest.json"
CLASS_ATTRIBUTE_SETS_FILENAME = "class_attribute_sets.json"
GROUND_TRUTH_FILENAME = "ground_truth.jsonl"
RAG_LABELS_DIR = Path(__file__).resolve().parent / "processed" / "rag_labels"

# Flat directory with raw PDFs for local runs (gitignored). Identified by pdf_filename.
RAW_PDF_DIR = _REPO_ROOT / "data.local" / "input_data" / "pdf"


def load_examples_manifest() -> list[dict]:
    path = PROCESSED_DIR / EXAMPLES_MANIFEST_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


def load_class_attribute_sets() -> dict[str, list[dict]]:
    path = PROCESSED_DIR / CLASS_ATTRIBUTE_SETS_FILENAME
    return json.loads(path.read_text(encoding="utf-8"))


def load_ground_truth() -> list[dict]:
    path = PROCESSED_DIR / GROUND_TRUTH_FILENAME
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]
