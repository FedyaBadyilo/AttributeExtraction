"""Table-aware line object linker.

Overrides dedoc's LineObjectLinker so that when a table is linked to the line
above it (caption above table), the TableAnnotation is placed at the *end* of
that line (start == end == len(line)), making the table appear after the caption
in the tree.  When linked to the line below, the annotation starts at 0 as in
the base class.
"""
from collections import defaultdict
from typing import List

from dedoc.data_structures.concrete_annotations.attach_annotation import AttachAnnotation
from dedoc.data_structures.concrete_annotations.table_annotation import TableAnnotation
from dedoc.data_structures.hierarchy_level import HierarchyLevel
from dedoc.data_structures.line_metadata import LineMetadata
from dedoc.readers.pdf_reader.data_classes.line_with_location import LineWithLocation
from dedoc.readers.pdf_reader.data_classes.pdf_image_attachment import PdfImageAttachment
from dedoc.readers.pdf_reader.data_classes.tables.scantable import ScanTable
from dedoc.readers.pdf_reader.utils.line_object_linker import LineObjectLinker


class TableAwareLineObjectLinker(LineObjectLinker):
    """LineObjectLinker that places TableAnnotation after the caption line."""

    def link_objects(
        self,
        lines: List[LineWithLocation],
        tables: List[ScanTable],
        images: List[PdfImageAttachment],
    ) -> List[LineWithLocation]:
        if not lines:
            from dedoc.readers.pdf_reader.data_classes.tables.location import Location
            from dedocutils.data_structures import BBox

            metadata = LineMetadata(
                tag_hierarchy_level=HierarchyLevel.create_unknown(), page_id=0, line_id=0
            )
            lines = [
                LineWithLocation(
                    line="",
                    metadata=metadata,
                    annotations=[],
                    location=Location(page_number=0, bbox=BBox(0, 0, 1, 1)),
                )
            ]

        last_page_line = self._get_last_page_line(lines)
        all_objects = list(lines) + list(tables) + list(images)
        all_objects.sort(key=lambda o: (o.location.page_number, o.order, o.location))

        objects_with_line_candidate: dict = defaultdict(dict)
        self._add_lines(all_objects, "previous_lines", objects_with_line_candidate)
        self._add_lines(all_objects[::-1], "next_lines", objects_with_line_candidate)

        for object_with_lines in objects_with_line_candidate.values():
            page_object = object_with_lines["object"]
            best_line = self._find_closest_line(
                page_object=page_object,
                lines_before=object_with_lines["previous_lines"],
                lines_after=object_with_lines["next_lines"],
                last_page_line=last_page_line,
            )
            if isinstance(page_object, ScanTable):
                previous_lines = object_with_lines["previous_lines"]
                if best_line in previous_lines:
                    pos = len(best_line.line)
                    annotation = TableAnnotation(value=page_object.uid, start=pos, end=pos)
                else:
                    annotation = TableAnnotation(
                        value=page_object.uid, start=0, end=len(best_line.line)
                    )
            elif isinstance(page_object, PdfImageAttachment):
                annotation = AttachAnnotation(
                    attach_uid=page_object.uid, start=0, end=len(best_line.line)
                )
            else:
                self.logger.warning("Unsupported page object type %s", page_object)
                if self.config.get("debug_mode", False):
                    raise RuntimeError(f"Unsupported page object type {page_object}")
                continue
            best_line.annotations.append(annotation)

        return lines


def _patch_reader_linker(reader, config) -> None:
    if hasattr(reader, "linker"):
        reader.linker = TableAwareLineObjectLinker(config=config)


def patch_dedoc_readers_with_table_aware_linker(readers, config):
    """Inject TableAwareLineObjectLinker into dedoc PDF readers that link tables."""
    from dedoc.readers.pdf_reader.pdf_auto_reader.pdf_auto_reader import PdfAutoReader

    patched = []
    for reader in readers:
        if type(reader) is PdfAutoReader:
            _patch_reader_linker(reader.pdf_txtlayer_reader, config)
            _patch_reader_linker(reader.pdf_tabby_reader, config)
            _patch_reader_linker(reader.pdf_image_reader, config)
        else:
            _patch_reader_linker(reader, config)
        patched.append(reader)
    return patched
