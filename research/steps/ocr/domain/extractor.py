"""Post-processed structure extractor for dedoc.

Applies four post-processing passes on top of DefaultStructureExtractor:
1. Split ``rule_part`` lines that contain both a numbered prefix and body text.
2. Fix adjacent headers where a lower ``level_2`` follows a higher one.
3. Align continuation headers that start with a lowercase letter.
4. Align adjacent headers at the same level that have different ``line_type``.
"""
from copy import deepcopy
from typing import Optional

from dedoc.data_structures import Annotation, HierarchyLevel, LineWithMeta, UnstructuredDocument
from dedoc.data_structures.concrete_annotations.attach_annotation import AttachAnnotation
from dedoc.data_structures.concrete_annotations.table_annotation import TableAnnotation
from dedoc.structure_extractors import DefaultStructureExtractor

from research.steps.ocr.domain.patterns import RULE_PART_REGEX
from research.steps.ocr.domain.tree_constructor import (
    line_has_table_or_attach_after_visible_text,
)


class PostProcessedStructureExtractor(DefaultStructureExtractor):
    """DefaultStructureExtractor extended with document-specific post-processing."""

    def extract(
        self, document: UnstructuredDocument, parameters: Optional[dict] = None
    ) -> UnstructuredDocument:
        document = super().extract(document, parameters)
        document.lines = self._split_rule_part_lines(document.lines)
        document.lines = self._fix_adjacent_header_levels(document.lines)
        document.lines = self._align_continuation_header_types(document.lines)
        document.lines = self._align_same_level_adjacent_header_types(document.lines)
        return document

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _copy_with_hierarchy(line: LineWithMeta, template: LineWithMeta) -> LineWithMeta:
        """Return *line* with its HierarchyLevel replaced by the one from *template*."""
        th = template.metadata.hierarchy_level
        new_hl = HierarchyLevel(
            line_type=th.line_type,
            level_1=th.level_1,
            level_2=th.level_2,
            can_be_multiline=th.can_be_multiline,
        )
        new_metadata = deepcopy(line.metadata)
        new_metadata.hierarchy_level = new_hl
        return LineWithMeta(
            line=line.line,
            metadata=new_metadata,
            annotations=line.annotations,
            uid=line.uid,
        )

    @staticmethod
    def _prev_blocks_alignment(prev: LineWithMeta) -> bool:
        """Return True when the previous line is a table/attachment caption."""
        return line_has_table_or_attach_after_visible_text(prev.line, prev.annotations)

    @staticmethod
    def _starts_with_lowercase(line: LineWithMeta) -> bool:
        for char in line.line.strip():
            if char.isalpha():
                return char.islower()
        return False

    # ------------------------------------------------------------------
    # Post-processing passes
    # ------------------------------------------------------------------

    def _split_rule_part_lines(self, lines: list[LineWithMeta]) -> list[LineWithMeta]:
        """Split 'rule_part' lines into a numbered prefix line and a body text line."""
        result: list[LineWithMeta] = []
        for line in lines:
            if line.metadata.hierarchy_level.line_type != "rule_part":
                result.append(line)
                continue
            m = RULE_PART_REGEX.match(line.line)
            if not m:
                result.append(line)
                continue
            start, end = m.start(), m.end()
            first_anns = self._select_annotations(line.annotations, start, end)
            result.append(
                LineWithMeta(
                    line=line.line[start:end],
                    metadata=line.metadata,
                    annotations=first_anns,
                    uid=line.uid,
                )
            )
            rest = line.line[end:]
            if rest:
                second_anns = self._select_annotations(line.annotations, end, len(line.line))
                metadata = deepcopy(line.metadata)
                metadata.hierarchy_level = HierarchyLevel.create_raw_text()
                result.append(
                    LineWithMeta(
                        line=rest,
                        metadata=metadata,
                        annotations=second_anns,
                        uid=line.uid + "_split",
                    )
                )
        return result

    def _fix_adjacent_header_levels(self, lines: list[LineWithMeta]) -> list[LineWithMeta]:
        """Align a header whose level_2 is lower than the preceding header's level_2."""
        if len(lines) < 2:
            return lines
        out: list[LineWithMeta] = []
        for i, line in enumerate(lines):
            if i == 0:
                out.append(line)
                continue
            prev = out[-1]
            hp, hc = prev.metadata.hierarchy_level, line.metadata.hierarchy_level
            if (
                hp.level_1 == 1
                and hc.level_1 == 1
                and hp.level_2 > hc.level_2
                and not self._prev_blocks_alignment(prev)
            ):
                line = self._copy_with_hierarchy(line, prev)
            out.append(line)
        return out

    def _align_continuation_header_types(
        self, lines: list[LineWithMeta]
    ) -> list[LineWithMeta]:
        """Align a header that continues the previous one (starts lowercase, same level)."""
        if len(lines) < 2:
            return lines
        out: list[LineWithMeta] = []
        for line in lines:
            if not out:
                out.append(line)
                continue
            prev = out[-1]
            hp, hc = prev.metadata.hierarchy_level, line.metadata.hierarchy_level
            if (
                hp.level_1 == 1
                and hc.level_1 == 1
                and hp.level_2 == hc.level_2
                and hp.line_type != hc.line_type
                and self._starts_with_lowercase(line)
                and not self._prev_blocks_alignment(prev)
            ):
                line = self._copy_with_hierarchy(line, prev)
            out.append(line)
        return out

    def _align_same_level_adjacent_header_types(
        self, lines: list[LineWithMeta]
    ) -> list[LineWithMeta]:
        """Align adjacent headers at the same level that have different line_types."""
        if len(lines) < 2:
            return lines
        out: list[LineWithMeta] = []
        for line in lines:
            if not out:
                out.append(line)
                continue
            prev = out[-1]
            hp, hc = prev.metadata.hierarchy_level, line.metadata.hierarchy_level
            same_level_diff_type = (
                hp.level_1 == 1
                and hc.level_1 == 1
                and hp.level_2 == hc.level_2
                and hp.line_type != hc.line_type
            )
            if same_level_diff_type and not self._prev_blocks_alignment(prev):
                line = self._copy_with_hierarchy(line, prev)
            out.append(line)
        return out

    @staticmethod
    def _select_annotations(annotations: list, start: int, end: int) -> list:
        """Slice annotations for a line segment, preserving table/attach types.

        Dedoc's default implementation rebuilds table/attach annotations as generic
        ``Annotation`` (``is_mergeable=True``). When several tables share one
        ``rule_part`` line, ``AnnotationMerger`` then drops all but one overlapping
        ``name="table"`` span. Keep concrete ``TableAnnotation`` /
        ``AttachAnnotation`` so ``is_mergeable=False`` survives through split and
        tree ``merge_annotations``.
        """
        assert start <= end
        res: list[Annotation] = []
        for annotation in annotations:
            if annotation.name in (TableAnnotation.name, AttachAnnotation.name):
                if start != 0:
                    continue
                if annotation.name == TableAnnotation.name:
                    res.append(TableAnnotation(value=annotation.value, start=start, end=end))
                else:
                    res.append(
                        AttachAnnotation(attach_uid=annotation.value, start=start, end=end)
                    )
                continue
            if annotation.end > start and annotation.start <= end:
                new_start = max(annotation.start, start) - start
                new_end = min(annotation.end, end) - start
                mergeable = getattr(annotation, "is_mergeable", True)
                res.append(
                    Annotation(
                        start=new_start,
                        end=new_end,
                        value=annotation.value,
                        name=annotation.name,
                        is_mergeable=mergeable,
                    )
                )
        return res
