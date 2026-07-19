"""Backend adapter: research.steps domain chain for one TZ package."""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from backend.app.schemas import TzPackageRead
from backend.app.services import file_cache
from research.steps.attribute_grouping.domain.models import AttributeGroups, ClassAttributeSet
from research.steps.extraction.domain.models import ExtractedAttributesDocument

if TYPE_CHECKING:
    from research.steps.chunking.domain.models import Chunk

DEFAULT_SEARCH_LIMIT = 10
EXTRACTIONS_FILENAME = "extractions.json"


@dataclass(frozen=True)
class PipelineTzResult:
    package_id: str
    tz_id: str
    collection_name: str
    output_path: Path
    extractions: ExtractedAttributesDocument
    source_chunks_path: Path | None = None
    source_chunks_by_attribute: dict[str, dict[int, str]] | None = None


@dataclass(frozen=True)
class _TzFileBundle:
    main: Path
    supplements_by_index: dict[int, Path]

    def all_paths(self) -> list[Path]:
        ordered = [self.main]
        for index in sorted(self.supplements_by_index):
            ordered.append(self.supplements_by_index[index])
        return ordered


def run_tz_pipeline(
    *,
    task_id: str,
    package: TzPackageRead,
    config: dict[str, Any],
    attr_set: ClassAttributeSet,
    semantic_groups: AttributeGroups,
    progress_callback: Callable[[str, str], None] | None = None,
) -> PipelineTzResult:
    """Run research.steps domain chain for one validated TZ package."""
    from infra.qdrant import get_qdrant_client
    from research.steps.chunking.domain import chunk_document
    from research.steps.context_grouping.domain import build_context_attribute_groups
    from research.steps.context_rebuild.domain import rebuild_grouped_context
    from research.steps.extraction.domain import run_extraction
    from research.steps.markdown_formatting.domain import format_document
    from research.steps.merge.domain.runner import run_merge
    from research.steps.ocr.domain import convert_document
    from research.steps.reranking.domain import run_reranking
    from research.steps.retrieval.domain import run_retrieval
    from research.steps.vectorizing.domain import index_chunks

    package_id = package.package_id or package.recpart or package.tz_id
    package_slug = _safe_collection_part(package_id)
    documents_root = file_cache.documents_dir(task_id)
    artifacts_root = file_cache.task_workspace(task_id) / "artifacts" / package_slug
    output_dir = file_cache.output_dir(task_id) / package_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    bundle = _TzFileBundle(
        main=documents_root / package.main_file_name,
        supplements_by_index={
            index: documents_root / file_name
            for index, file_name in package.supplements_by_index.items()
        },
    )
    _ensure_bundle_files_exist(bundle.all_paths())

    collection_name = _collection_name(config, task_id, package.tz_id)
    retrieval_cfg = config.get("RETRIEVAL") or {}
    search_limit = int(retrieval_cfg.get("limit", DEFAULT_SEARCH_LIMIT))

    ocr_output_dir = artifacts_root / "ocr"
    all_chunks: list[Any] = []
    for file_path in bundle.all_paths():
        _report_progress(progress_callback, "ocr", f"Чтение PDF-файла {file_path.name} для пакета {package.tz_id}")
        parsed = convert_document(
            file_path=file_path,
            output_dir=ocr_output_dir,
            config=config,
            attachments_subdir=file_path.stem,
        )
        _report_progress(
            progress_callback,
            "markdown_formatting",
            f"Подготовка текста файла {file_path.name} для пакета {package.tz_id}",
        )
        formatted = format_document(parsed.content)
        _report_progress(
            progress_callback,
            "chunking",
            f"Разделение файла {file_path.name} на фрагменты для пакета {package.tz_id}",
        )
        document = chunk_document(
            formatted,
            eos_id=0,
            pdf_filename=file_path.name,
            config=config,
        )
        all_chunks.extend(document.chunks)

    if not all_chunks:
        raise RuntimeError(f"Не удалось получить чанки для пакета {package.tz_id}")

    _report_progress(progress_callback, "vectorizing", f"Подготовка поиска для пакета {package.tz_id}")
    index_chunks(all_chunks, config, collection_name)

    _report_progress(progress_callback, "retrieval", f"Поиск нужных фрагментов для пакета {package.tz_id}")
    search_rows = run_retrieval(
        attr_set.attributes,
        collection_name,
        config,
        limit=search_limit,
        execution_variant=package.execution_variant,
    )
    merge_results = run_merge(search_rows, collection_name, config)
    source_chunks_by_attribute = _source_chunks_by_attribute(merge_results)
    priority_by_point_id = _priority_by_point_id(
        search_rows,
        main_file_name=package.main_file_name,
        supplements_by_index=package.supplements_by_index,
    )

    _report_progress(progress_callback, "reranking", f"Сбор и группировка фрагментов для пакета {package.tz_id}")
    rerank_result = run_reranking(
        merge_results,
        attr_set,
        config,
        priority_by_point_id=priority_by_point_id,
        execution_variant=package.execution_variant,
    )
    context_groups = build_context_attribute_groups(
        rerank_result,
        attr_set,
        config,
        semantic_groups,
    )
    qdrant = get_qdrant_client(config)
    grouped = rebuild_grouped_context(
        context_groups,
        rerank_result,
        merge_results,
        qdrant,
        collection_name,
    )

    _report_progress(progress_callback, "extraction", f"Извлечение атрибутов для пакета {package.tz_id}")
    extractions = run_extraction(
        grouped,
        attr_set,
        config,
        priority_by_point_id=priority_by_point_id,
        execution_variant=package.execution_variant,
    )

    output_path = output_dir / EXTRACTIONS_FILENAME
    source_chunks_path = output_dir / "source_chunks.json"
    _write_extractions(output_path, extractions)
    _write_source_chunks(source_chunks_path, source_chunks_by_attribute)
    return PipelineTzResult(
        package_id=package_id,
        tz_id=package.tz_id,
        collection_name=collection_name,
        output_path=output_path,
        extractions=extractions,
        source_chunks_path=source_chunks_path,
        source_chunks_by_attribute=source_chunks_by_attribute,
    )


def load_tz_pipeline_result(
    *,
    package_id: str,
    tz_id: str,
    collection_name: str,
    output_path: Path,
) -> PipelineTzResult:
    with output_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    source_chunks_path = _existing_source_chunks_path(output_path)
    return PipelineTzResult(
        package_id=package_id,
        tz_id=tz_id,
        collection_name=collection_name,
        output_path=output_path,
        extractions=ExtractedAttributesDocument.model_validate(payload),
        source_chunks_path=source_chunks_path,
        source_chunks_by_attribute=_load_source_chunks(source_chunks_path),
    )


def _ensure_bundle_files_exist(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Не найдены PDF-файлы из комплекта: {missing}")


def _collection_name(config: dict[str, Any], task_id: str, tz_id: str) -> str:
    template = (
        config.get("BACKEND_QDRANT_COLLECTION_TEMPLATE")
        or "AttributeExtractor-{task_id}-{tz_id}"
    )
    return str(template).format(
        task_id=_safe_collection_part(task_id),
        tz_id=_safe_collection_part(tz_id),
    )


def _safe_collection_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return normalized.strip("._-") or "unknown"


def _report_progress(callback: Callable[[str, str], None] | None, step: str, message: str) -> None:
    if callback is not None:
        callback(step, message)


def _priority_by_point_id(
    search_rows: list[Any],
    *,
    main_file_name: str,
    supplements_by_index: dict[int, str],
) -> dict[int, int]:
    priority_by_filename = {main_file_name: 100}
    for index, name in sorted(supplements_by_index.items()):
        priority_by_filename[name] = 100 - int(index)
    return {
        hit.id: priority_by_filename.get(hit.payload.metadata.file_name, 0)
        for row in search_rows
        for hit in row.chunks
    }


def _write_extractions(path: Path, extractions: ExtractedAttributesDocument) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as file:
        json.dump(extractions.model_dump(mode="json"), file, ensure_ascii=False, indent=2)
        temp_path = Path(file.name)
    temp_path.replace(path)


def _source_chunks_by_attribute(merge_results: list[Any]) -> dict[str, dict[int, str]]:
    out: dict[str, dict[int, str]] = {}
    for result in merge_results:
        chunks: dict[int, str] = {}
        for chunk in result.merged_chunks:
            chunks[int(chunk.display_point_id)] = chunk.content
        out[str(result.attribute_id)] = chunks
    return out


def _write_source_chunks(path: Path, source_chunks_by_attribute: dict[str, dict[int, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        attribute_id: {str(chunk_id): text for chunk_id, text in chunks.items()}
        for attribute_id, chunks in source_chunks_by_attribute.items()
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        temp_path = Path(file.name)
    temp_path.replace(path)


def _existing_source_chunks_path(output_path: Path) -> Path | None:
    path = output_path.with_name("source_chunks.json")
    return path if path.is_file() else None


def _load_source_chunks(path: Path | None) -> dict[str, dict[int, str]] | None:
    if path is None:
        return None
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        return None
    out: dict[str, dict[int, str]] = {}
    for attribute_id, chunks in payload.items():
        if not isinstance(chunks, dict):
            continue
        out[str(attribute_id)] = {
            int(chunk_id): str(text)
            for chunk_id, text in chunks.items()
            if str(chunk_id).isdigit()
        }
    return out
