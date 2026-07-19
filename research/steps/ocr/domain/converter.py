"""PDF → dedoc ParsedDocument conversion with the custom pipeline.

Assembles a DedocManager configured with:
- PostProcessedStructureExtractor (custom post-processing passes)
- CustomTreeConstructor (annotation-shift fix + table-aware multiline blocking)
- TableAwareLineObjectLinker injected into dedoc PDF readers (Txtlayer, Tabby, and OCR paths)

Public API: ``convert_document(file_path, output_dir, *, config)``.
"""
from pathlib import Path
from typing import Any

from dedoc import DedocManager
from dedoc.api.schema.parsed_document import ParsedDocument
from dedoc.config import get_config
from dedoc.manager_config import get_manager_config
from dedoc.readers.reader_composition import ReaderComposition
from dedoc.structure_constructors.concrete_structure_constructors.linear_constructor import (
    LinearConstructor,
)
from dedoc.structure_constructors.structure_constructor_composition import (
    StructureConstructorComposition,
)
from dedoc.structure_extractors.structure_extractor_composition import (
    StructureExtractorComposition,
)

from research.steps.ocr.domain.dedoc_parameters import DEDOC_SCALAR_PARAMETERS
from research.steps.ocr.domain.extractor import PostProcessedStructureExtractor
from research.steps.ocr.domain.linker import patch_dedoc_readers_with_table_aware_linker
from research.steps.ocr.domain.patterns import PATTERNS_LIST
from research.steps.ocr.domain.tree_constructor import CustomTreeConstructor

_DEDOC_PARAMETERS = {**DEDOC_SCALAR_PARAMETERS, "patterns": PATTERNS_LIST}


def _build_dedoc_manager(pipeline_config: dict[str, Any]) -> DedocManager:
    dedoc_config = get_config()
    ocr_cfg = pipeline_config.get("OCR") or {}
    dedoc_config["on_gpu"] = bool(ocr_cfg.get("on_gpu", False))

    base_manager_config = get_manager_config(dedoc_config)

    structure_extractor = StructureExtractorComposition(
        extractors={"other": PostProcessedStructureExtractor()},
        default_key="other",
        config=dedoc_config,
    )
    structure_constructor = StructureConstructorComposition(
        constructors={"linear": LinearConstructor(), "tree": CustomTreeConstructor()},
        default_constructor=CustomTreeConstructor(),
    )

    manager_config = dict(base_manager_config)
    manager_config["structure_extractor"] = structure_extractor
    manager_config["structure_constructor"] = structure_constructor

    readers = patch_dedoc_readers_with_table_aware_linker(
        base_manager_config["reader"].readers,
        dedoc_config,
    )
    manager_config["reader"] = ReaderComposition(readers=readers)

    return DedocManager(config=dedoc_config, manager_config=manager_config)


def convert_document(
    file_path: Path,
    output_dir: Path,
    *,
    config: dict[str, Any],
    attachments_subdir: str | None = None,
) -> ParsedDocument:
    """Parse *file_path* with the custom dedoc pipeline and return the API schema.

    Args:
        file_path: Path to the PDF file.
        output_dir: Directory where dedoc will write extracted attachments.
        config: Repository config dict (loaded via ``infra.config.loader``).
        attachments_subdir: Optional sub-directory inside ``output_dir/attachments/``
            for attachment isolation when processing multiple files for the same document.
    """
    manager = _build_dedoc_manager(config)
    attachments_dir = output_dir / "attachments"
    if attachments_subdir is not None:
        attachments_dir = attachments_dir / attachments_subdir

    parameters = dict(_DEDOC_PARAMETERS)
    parameters["attachments_dir"] = attachments_dir

    parsed = manager.parse(file_path=str(file_path.resolve()), parameters=parameters)
    return parsed.to_api_schema()
