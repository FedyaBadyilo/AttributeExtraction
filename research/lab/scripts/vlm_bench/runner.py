"""Build document-parsing-compatible snapshots via page-wise VLM Markdown."""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from tqdm import tqdm

from infra.config.loader import get_config_and_env
from infra.llm.openai import get_openai_llm
from infra.llm_observability.langfuse import get_langfuse_handler
from research.benchmarks.document_parsing.artifacts import (
    write_case_artifacts,
    write_json,
    write_run_metadata,
)
from research.benchmarks.document_parsing.manifest import (
    DEFAULT_MANIFEST_PATH,
    REPOSITORY_ROOT,
    compute_dataset_digest,
    load_manifest,
    resolve_repo_path,
)
from research.benchmarks.document_parsing.models import BenchmarkCase, BenchmarkManifest
from research.lab.scripts.vlm_bench.prompt import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    user_prompt,
)
from research.lab.scripts.vlm_bench.render import (
    count_pdf_pages,
    png_to_data_url,
    render_pdf_pages_png,
)

DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / "research/lab/output/vlm_bench"
_FENCE_RE = re.compile(
    r"^\s*```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$",
    re.IGNORECASE,
)


def _strip_outer_fence(text: str) -> str:
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group(1).strip()
    return text.strip()


def _case_is_complete(case_dir: Path) -> bool:
    return (
        (case_dir / "gt.md").is_file()
        and (case_dir / "pred.raw.md").is_file()
        and (case_dir / "intermediates" / "ocr.json").is_file()
        and (case_dir / "intermediates" / "formatted.json").is_file()
    )


def _invoke_page(
    llm: Any,
    *,
    png_bytes: bytes,
    page_index: int,
    page_count: int,
    case_id: str,
    callbacks: list[Any] | None = None,
) -> tuple[str, dict[str, Any], float]:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {"type": "text", "text": user_prompt(page_index=page_index, page_count=page_count)},
                {
                    "type": "image_url",
                    "image_url": {"url": png_to_data_url(png_bytes)},
                },
            ]
        ),
    ]
    run_name = f"vlm_bench[{case_id}|p{page_index + 1}/{page_count}]"
    invoke_kwargs: dict[str, Any] = {}
    if callbacks:
        invoke_kwargs["config"] = {
            "callbacks": callbacks,
            "run_name": run_name,
            "metadata": {"langfuse_trace_name": run_name},
        }
    started = time.perf_counter()
    response = llm.invoke(messages, **invoke_kwargs)
    elapsed = time.perf_counter() - started
    content = response.content if isinstance(response.content, str) else str(response.content)
    usage: dict[str, Any] = {}
    meta = getattr(response, "usage_metadata", None)
    if isinstance(meta, dict):
        usage = meta
    elif meta is not None:
        usage = dict(meta)
    return _strip_outer_fence(content), usage, elapsed


def _run_case(
    case: BenchmarkCase,
    *,
    repo_root: Path,
    output_dir: Path,
    llm: Any,
    model_key: str,
    model_name: str,
    dpi: int,
    callbacks: list[Any] | None = None,
    progress: tqdm | None = None,
) -> None:
    pdf_path = resolve_repo_path(repo_root, case.input.path)
    reference_bytes = resolve_repo_path(repo_root, case.reference_path).read_bytes()
    pages_png = render_pdf_pages_png(pdf_path=pdf_path, dpi=dpi)
    page_count = len(pages_png)
    if page_count == 0:
        raise ValueError(f"PDF has no pages: {pdf_path}")

    page_markdowns: list[str] = []
    page_records: list[dict[str, Any]] = []
    for page_index, png_bytes in enumerate(pages_png):
        if progress is not None:
            progress.set_postfix_str(
                f"{case.case_id} p{page_index + 1}/{page_count}", refresh=False
            )
        markdown, usage, elapsed = _invoke_page(
            llm,
            png_bytes=png_bytes,
            page_index=page_index,
            page_count=page_count,
            case_id=case.case_id,
            callbacks=callbacks,
        )
        raw_name = f"page-{page_index + 1:03d}.raw.md"
        page_markdowns.append(markdown)
        page_records.append(
            {
                "page_index": page_index,
                "elapsed_seconds": elapsed,
                "raw_path": f"intermediates/pages/{raw_name}",
                "usage": usage,
                "raw_name": raw_name,
                "markdown": markdown,
            }
        )
        if progress is not None:
            progress.update(1)

    prediction = "\n\n".join(page_markdowns).strip() + "\n"
    ocr_pages = [
        {
            "page_index": record["page_index"],
            "elapsed_seconds": record["elapsed_seconds"],
            "raw_path": record["raw_path"],
            "usage": record["usage"],
        }
        for record in page_records
    ]
    ocr = {
        "backend": "vlm_page_markdown",
        "prompt_version": PROMPT_VERSION,
        "model_key": model_key,
        "model": model_name,
        "dpi": dpi,
        "page_count": page_count,
        "pages": ocr_pages,
    }
    formatted = {
        "backend": "vlm_page_markdown",
        "note": (
            "Prediction is concatenated per-page Markdown; "
            "no FormattedDocument / structure tree."
        ),
        "prompt_version": PROMPT_VERSION,
        "page_count": page_count,
    }
    write_case_artifacts(
        output_dir,
        case_id=case.case_id,
        reference_bytes=reference_bytes,
        prediction=prediction,
        ocr=ocr,
        formatted=formatted,
    )
    pages_dir = output_dir / "cases" / case.case_id / "intermediates" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=False)
    for record in page_records:
        (pages_dir / record["raw_name"]).write_text(
            record["markdown"] + "\n", encoding="utf-8"
        )


def run_vlm_bench(
    *,
    model_key: str,
    dpi: int = 96,
    run_id: str | None = None,
    case_ids: list[str] | None = None,
    resume: bool = False,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    repo_root: Path = REPOSITORY_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    config: dict[str, Any] | None = None,
) -> Path:
    """Materialize a snapshot under ``output_root / run_id`` and return that path.

    Fail-fast on the first case error. With ``resume=True``, completed cases are
    skipped so a failed run can be continued in the same directory.
    """
    pipeline_config = get_config_and_env() if config is None else config
    if model_key not in pipeline_config["MODELS"]:
        raise KeyError(f"MODELS has no key {model_key!r}")

    model_cfg = pipeline_config["MODELS"][model_key]
    model_name = str(model_cfg["model"])
    resolved_run_id = run_id or f"{model_key}-dpi{dpi}-{PROMPT_VERSION}"
    output_dir = output_root / resolved_run_id

    manifest = load_manifest(manifest_path, repo_root=repo_root)

    selected = list(manifest.cases)
    if case_ids is not None:
        wanted = set(case_ids)
        known = {case.case_id for case in manifest.cases}
        missing = sorted(wanted - known)
        if missing:
            raise ValueError(f"unknown case_id(s): {missing}")
        selected = [case for case in manifest.cases if case.case_id in wanted]

    snapshot_manifest = (
        manifest
        if case_ids is None
        else manifest.model_copy(update={"cases": selected})
    )
    dataset_digest = compute_dataset_digest(snapshot_manifest, repo_root=repo_root)

    if output_dir.exists() and not resume:
        raise FileExistsError(
            f"output already exists: {output_dir}. Pass --resume to continue, "
            "or choose a new --run-id."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_run_metadata(
        output_dir,
        manifest=snapshot_manifest,
        dataset_digest=dataset_digest,
    )
    write_json(
        output_dir / "run_params.json",
        {
            "experiment": "E007",
            "backend": "vlm_page_markdown",
            "prompt_version": PROMPT_VERSION,
            "model_key": model_key,
            "model": model_name,
            "dpi": dpi,
            "unit_of_call": "page",
            "case_ids": [case.case_id for case in selected] if case_ids else "all",
            "resume": resume,
        },
    )

    llm = get_openai_llm(model_key, pipeline_config)
    langfuse_handler = get_langfuse_handler()
    callbacks: list[Any] = [langfuse_handler] if langfuse_handler else []

    pending: list[tuple[BenchmarkCase, int]] = []
    skipped = 0
    for case in selected:
        case_dir = output_dir / "cases" / case.case_id
        if resume and _case_is_complete(case_dir):
            skipped += 1
            continue
        pdf_path = resolve_repo_path(repo_root, case.input.path)
        page_count = count_pdf_pages(pdf_path)
        if page_count == 0:
            raise ValueError(f"PDF has no pages: {pdf_path}")
        pending.append((case, page_count))

    total_pages = sum(page_count for _, page_count in pending)
    tqdm.write(
        f"vlm_bench {model_key}: {len(pending)} cases / {total_pages} pages"
        + (f" (skip {skipped} complete)" if skipped else "")
    )

    with tqdm(
        total=total_pages,
        desc="vlm pages",
        unit="page",
        dynamic_ncols=True,
    ) as progress:
        for case, _page_count in pending:
            case_dir = output_dir / "cases" / case.case_id
            if case_dir.exists():
                # Incomplete leftover from a failed attempt — rebuild cleanly.
                shutil.rmtree(case_dir)
            _run_case(
                case,
                repo_root=repo_root,
                output_dir=output_dir,
                llm=llm,
                model_key=model_key,
                model_name=model_name,
                dpi=dpi,
                callbacks=callbacks,
                progress=progress,
            )

    return output_dir


def assert_snapshot_ready_for_eval(output_dir: Path, manifest: BenchmarkManifest) -> None:
    """Require every manifest case to be complete (eval adapter contract)."""
    missing = [
        case.case_id
        for case in manifest.cases
        if not _case_is_complete(output_dir / "cases" / case.case_id)
    ]
    if missing:
        raise FileNotFoundError(
            "snapshot is incomplete for eval reuse; missing or incomplete cases: "
            + ", ".join(missing)
        )


__all__ = [
    "DEFAULT_OUTPUT_ROOT",
    "assert_snapshot_ready_for_eval",
    "run_vlm_bench",
]
