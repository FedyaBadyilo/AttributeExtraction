"""Manifest loading, preflight checks, and deterministic dataset digest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from research.benchmarks.document_parsing.models import BenchmarkManifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH = Path("research/datasets/ocr_benchmark/manifest.json")
_DIGEST_DOMAIN = b"document-parsing-benchmark-dataset-v1\0"


def resolve_repo_path(repo_root: Path, relative_path: Path) -> Path:
    """Resolve a validated manifest path and reject symlink escapes."""
    root = repo_root.resolve()
    resolved = (root / relative_path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"path resolves outside repository: {relative_path.as_posix()}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest_files(manifest: BenchmarkManifest, *, repo_root: Path) -> None:
    """Check all referenced files and the declared benchmark-input hashes."""
    for case in manifest.cases:
        source_path = resolve_repo_path(repo_root, case.source.path)
        input_path = resolve_repo_path(repo_root, case.input.path)
        reference_path = resolve_repo_path(repo_root, case.reference_path)

        for role, path in (
            ("source", source_path),
            ("input", input_path),
            ("reference", reference_path),
        ):
            if not path.is_file():
                raise FileNotFoundError(f"{role} file for case {case.case_id} not found: {path}")

        actual_sha256 = sha256_file(input_path)
        if actual_sha256 != case.input.sha256:
            raise ValueError(
                f"input sha256 mismatch for case {case.case_id}: "
                f"expected {case.input.sha256}, got {actual_sha256}"
            )


def load_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    repo_root: Path = REPOSITORY_ROOT,
) -> BenchmarkManifest:
    """Load manifest v1 and complete all filesystem preflight checks."""
    path = manifest_path if manifest_path.is_absolute() else repo_root / manifest_path
    manifest = BenchmarkManifest.model_validate_json(path.read_text(encoding="utf-8"))
    validate_manifest_files(manifest, repo_root=repo_root)
    return manifest


def compute_dataset_digest(manifest: BenchmarkManifest, *, repo_root: Path) -> str:
    """Hash stable case identities, input hashes, and exact reference bytes.

    Cases are sorted by ``case_id`` so reordering the manifest does not change the
    identity of the dataset. Length-prefixing keeps byte boundaries unambiguous.
    """
    references = {
        case.case_id: resolve_repo_path(repo_root, case.reference_path).read_bytes()
        for case in manifest.cases
    }
    return compute_dataset_digest_from_references(manifest, references=references)


def compute_dataset_digest_from_references(
    manifest: BenchmarkManifest,
    *,
    references: dict[str, bytes],
) -> str:
    """Compute the dataset identity from an explicit reference snapshot."""
    expected_case_ids = {case.case_id for case in manifest.cases}
    if set(references) != expected_case_ids:
        raise ValueError("reference snapshot case IDs do not match manifest cases")

    digest = hashlib.sha256()
    digest.update(_DIGEST_DOMAIN)
    digest.update(manifest.schema_version.to_bytes(4, byteorder="big"))

    for case in sorted(manifest.cases, key=lambda item: item.case_id):
        metadata = json.dumps(
            {"case_id": case.case_id, "input_sha256": case.input.sha256},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        reference = references[case.case_id]
        for value in (metadata, reference):
            digest.update(len(value).to_bytes(8, byteorder="big"))
            digest.update(value)

    return digest.hexdigest()


__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "REPOSITORY_ROOT",
    "compute_dataset_digest",
    "compute_dataset_digest_from_references",
    "load_manifest",
    "resolve_repo_path",
    "sha256_file",
    "validate_manifest_files",
]
