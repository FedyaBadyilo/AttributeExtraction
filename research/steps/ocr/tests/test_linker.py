"""Contract tests for TableAwareLineObjectLinker injection."""

from dedoc.config import get_config
from dedoc.manager_config import get_manager_config
from dedoc.readers.pdf_reader.pdf_auto_reader.pdf_auto_reader import PdfAutoReader
from dedoc.readers.pdf_reader.pdf_image_reader.pdf_image_reader import PdfImageReader
from dedoc.readers.pdf_reader.pdf_txtlayer_reader.pdf_tabby_reader import PdfTabbyReader
from dedoc.readers.pdf_reader.pdf_txtlayer_reader.pdf_txtlayer_reader import PdfTxtlayerReader

from research.steps.ocr.domain.converter import _build_dedoc_manager
from research.steps.ocr.domain.linker import (
    TableAwareLineObjectLinker,
    patch_dedoc_readers_with_table_aware_linker,
)


def test_patch_replaces_top_level_tabby_reader_linker():
    dedoc_config = get_config()
    readers = patch_dedoc_readers_with_table_aware_linker(
        get_manager_config(dedoc_config)["reader"].readers,
        dedoc_config,
    )

    tabby_readers = [r for r in readers if type(r) is PdfTabbyReader]
    assert len(tabby_readers) == 1
    assert isinstance(tabby_readers[0].linker, TableAwareLineObjectLinker)


def test_patch_replaces_top_level_image_reader_linker():
    dedoc_config = get_config()
    readers = patch_dedoc_readers_with_table_aware_linker(
        get_manager_config(dedoc_config)["reader"].readers,
        dedoc_config,
    )

    image_readers = [r for r in readers if type(r) is PdfImageReader]
    assert len(image_readers) == 1
    assert isinstance(image_readers[0].linker, TableAwareLineObjectLinker)


def test_patch_replaces_pdf_auto_reader_internal_readers():
    dedoc_config = get_config()
    readers = patch_dedoc_readers_with_table_aware_linker(
        get_manager_config(dedoc_config)["reader"].readers,
        dedoc_config,
    )

    auto_readers = [r for r in readers if type(r) is PdfAutoReader]
    assert len(auto_readers) == 1
    auto_reader = auto_readers[0]
    assert type(auto_reader.pdf_txtlayer_reader) is PdfTxtlayerReader
    assert isinstance(auto_reader.pdf_txtlayer_reader.linker, TableAwareLineObjectLinker)
    assert type(auto_reader.pdf_tabby_reader) is PdfTabbyReader
    assert isinstance(auto_reader.pdf_tabby_reader.linker, TableAwareLineObjectLinker)
    assert auto_reader.txtlayer_detector.pdf_reader is auto_reader.pdf_tabby_reader
    assert isinstance(auto_reader.pdf_image_reader.linker, TableAwareLineObjectLinker)


def test_build_dedoc_manager_uses_table_aware_linker_for_auto_modes():
    manager = _build_dedoc_manager({"OCR": {"on_gpu": False}})
    readers = manager.reader.readers

    auto_reader = next(r for r in readers if type(r) is PdfAutoReader)
    assert isinstance(auto_reader.pdf_txtlayer_reader.linker, TableAwareLineObjectLinker)
    assert isinstance(auto_reader.pdf_tabby_reader.linker, TableAwareLineObjectLinker)
    assert isinstance(auto_reader.pdf_image_reader.linker, TableAwareLineObjectLinker)

    tabby_reader = next(r for r in readers if type(r) is PdfTabbyReader)
    assert isinstance(tabby_reader.linker, TableAwareLineObjectLinker)

    txtlayer_reader = next(r for r in readers if type(r) is PdfTxtlayerReader)
    assert isinstance(txtlayer_reader.linker, TableAwareLineObjectLinker)

    image_reader = next(r for r in readers if type(r) is PdfImageReader)
    assert isinstance(image_reader.linker, TableAwareLineObjectLinker)

    for mode in ("auto", "auto_tabby"):
        params = {"pdf_with_text_layer": mode}
        first_match = next(
            r
            for r in readers
            if r.can_read(file_path="test.pdf", extension=".pdf", parameters=params)
        )
        assert type(first_match) is PdfAutoReader
