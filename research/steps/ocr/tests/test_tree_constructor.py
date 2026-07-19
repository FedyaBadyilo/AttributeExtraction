"""Unit tests for annotation helpers in tree_constructor.py."""
from dedoc.data_structures.annotation import Annotation
from dedoc.data_structures.concrete_annotations.attach_annotation import AttachAnnotation
from dedoc.data_structures.concrete_annotations.table_annotation import TableAnnotation

from research.steps.ocr.domain.tree_constructor import (
    _shift_annotations_preserve_mergeable,
    line_has_table_or_attach_after_visible_text,
)
from research.steps.ocr.tests.fixtures import make_line


class TestLineHasTableOrAttachAfterVisibleText:
    def test_table_after_visible_text(self):
        line = make_line("Таблица 1")
        # Table annotation starts at position 9 (after "Таблица 1") — i.e. after visible text
        table_ann = TableAnnotation(value="tbl_uid", start=9, end=9)
        line.annotations.append(table_ann)
        assert line_has_table_or_attach_after_visible_text(line.line, line.annotations) is True

    def test_table_at_start_of_empty_line(self):
        line = make_line("")
        table_ann = TableAnnotation(value="tbl_uid", start=0, end=0)
        line.annotations.append(table_ann)
        assert line_has_table_or_attach_after_visible_text(line.line, line.annotations) is False

    def test_no_table_annotations(self):
        line = make_line("просто текст")
        assert line_has_table_or_attach_after_visible_text(line.line, line.annotations) is False

    def test_attach_annotation_at_start(self):
        line = make_line("рис.")
        attach_ann = AttachAnnotation(attach_uid="att_uid", start=0, end=4)
        line.annotations.append(attach_ann)
        # start == 0 == first visible char → not "after" visible text
        assert line_has_table_or_attach_after_visible_text(line.line, line.annotations) is False


class TestShiftAnnotationsPreserveMergeable:
    def test_plain_annotation_shifted(self):
        line = make_line("hello")
        ann = Annotation(start=0, end=5, name="bold", value="True", is_mergeable=True)
        line.annotations.append(ann)
        shifted = _shift_annotations_preserve_mergeable(line, text_length=10)
        assert shifted[0].start == 10
        assert shifted[0].end == 15
        assert shifted[0].is_mergeable is True

    def test_table_annotation_stays_table_type(self):
        line = make_line("caption")
        t_ann = TableAnnotation(value="tbl_uid", start=7, end=7)
        line.annotations.append(t_ann)
        shifted = _shift_annotations_preserve_mergeable(line, text_length=3)
        result = shifted[0]
        assert isinstance(result, TableAnnotation)
        assert result.start == 10
        assert result.end == 10

    def test_attach_annotation_stays_attach_type(self):
        line = make_line("рис.")
        a_ann = AttachAnnotation(attach_uid="att_uid", start=0, end=4)
        line.annotations.append(a_ann)
        shifted = _shift_annotations_preserve_mergeable(line, text_length=5)
        result = shifted[0]
        assert isinstance(result, AttachAnnotation)
        assert result.start == 5
        assert result.end == 9
