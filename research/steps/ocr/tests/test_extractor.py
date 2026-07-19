"""Unit tests for PostProcessedStructureExtractor post-processing passes.

Tests exercise the deterministic static/instance methods directly without
calling dedoc's full extraction pipeline.
"""
from dedoc.data_structures import HierarchyLevel
from dedoc.data_structures.concrete_annotations.table_annotation import TableAnnotation

from research.steps.ocr.domain.extractor import PostProcessedStructureExtractor
from research.steps.ocr.domain.patterns import RULE_PART_REGEX
from research.steps.ocr.tests.fixtures import make_line

extractor = PostProcessedStructureExtractor()


class TestSplitRulePartLines:
    def test_splits_numbered_prefix_from_body(self):
        line = make_line("1.2 Текст требования", line_type="rule_part", uid="r1")
        result = extractor._split_rule_part_lines([line])
        assert len(result) == 2
        # First part: the numbered prefix matched by RULE_PART_REGEX
        prefix_match = RULE_PART_REGEX.match("1.2 Текст требования")
        assert prefix_match is not None
        assert result[0].line == "1.2 Текст требования"[: prefix_match.end()]
        assert result[0].uid == "r1"
        # Second part: remainder
        assert result[1].line == "Текст требования"
        assert result[1].uid == "r1_split"
        assert result[1].metadata.hierarchy_level.line_type == "raw_text"

    def test_no_split_when_no_match(self):
        line = make_line("просто текст", line_type="rule_part")
        result = extractor._split_rule_part_lines([line])
        assert len(result) == 1

    def test_non_rule_part_lines_pass_through(self):
        line = make_line("1.2 Текст", line_type="header")
        result = extractor._split_rule_part_lines([line])
        assert len(result) == 1
        assert result[0] is line

    def test_no_split_when_no_body_after_prefix(self):
        # "1." alone — prefix only, nothing after
        line = make_line("1.", line_type="rule_part")
        result = extractor._split_rule_part_lines([line])
        assert len(result) == 1
        assert result[0].line == "1."

    def test_keeps_multiple_table_annotations_on_prefix(self):
        """Two tables on one rule_part must both survive split as TableAnnotation.

        Dedoc's stock _select_annotations rebuilds them as mergeable Annotation;
        AnnotationMerger then drops all but one overlapping name=\"table\" span.
        """
        from dedoc.utils.annotation_merger import AnnotationMerger

        text = "3.4.3 В целях обеспечения сервисного обслуживания"
        line = make_line(text, line_type="rule_part", uid="r_dual")
        line.annotations.extend(
            [
                TableAnnotation(value="header-table-uid", start=0, end=len(text)),
                TableAnnotation(value="orphan-table-uid", start=0, end=len(text)),
            ]
        )
        result = extractor._split_rule_part_lines([line])
        assert len(result) == 2
        prefix = result[0]
        table_anns = [a for a in prefix.annotations if a.name == "table"]
        assert len(table_anns) == 2
        assert {a.value for a in table_anns} == {"header-table-uid", "orphan-table-uid"}
        assert all(isinstance(a, TableAnnotation) for a in table_anns)
        assert all(a.is_mergeable is False for a in table_anns)

        merged = AnnotationMerger().merge_annotations(prefix.annotations, prefix.line)
        merged_tables = [a for a in merged if a.name == "table"]
        assert {a.value for a in merged_tables} == {"header-table-uid", "orphan-table-uid"}


class TestFixAdjacentHeaderLevels:
    def test_lowers_level_2_of_header_following_higher_level_2(self):
        # prev has level_2=3, current has level_2=1 → current should be lifted to level_2=3
        prev = make_line("3.1.1 Заголовок", line_type="rule_part", level_1=1, level_2=3)
        curr = make_line("Подзаголовок", line_type="header", level_1=1, level_2=1)
        result = extractor._fix_adjacent_header_levels([prev, curr])
        assert result[1].metadata.hierarchy_level.level_2 == 3

    def test_no_change_when_prev_has_table_annotation(self):
        prev = make_line("Таблица 1", line_type="rule_part", level_1=1, level_2=3)
        table_ann = TableAnnotation(value="tbl_uid", start=9, end=9)
        prev.annotations.append(table_ann)
        curr = make_line("Подзаголовок", line_type="header", level_1=1, level_2=1)
        result = extractor._fix_adjacent_header_levels([prev, curr])
        # Must not realign across a table caption
        assert result[1].metadata.hierarchy_level.level_2 == 1


class TestAlignContinuationHeaderTypes:
    def test_aligns_lowercase_continuation(self):
        prev = make_line("ЗАГОЛОВОК", line_type="header", level_1=1, level_2=1)
        curr = make_line("продолжение заголовка", line_type="subheader", level_1=1, level_2=1)
        result = extractor._align_continuation_header_types([prev, curr])
        assert result[1].metadata.hierarchy_level.line_type == "header"

    def test_no_align_uppercase_start(self):
        prev = make_line("ЗАГОЛОВОК", line_type="header", level_1=1, level_2=1)
        curr = make_line("Продолжение", line_type="subheader", level_1=1, level_2=1)
        result = extractor._align_continuation_header_types([prev, curr])
        assert result[1].metadata.hierarchy_level.line_type == "subheader"


class TestAlignSameLevelAdjacentHeaderTypes:
    def test_aligns_different_type_same_level(self):
        prev = make_line("ЗАГОЛОВОК", line_type="header", level_1=1, level_2=2)
        curr = make_line("Параграф", line_type="subheader", level_1=1, level_2=2)
        result = extractor._align_same_level_adjacent_header_types([prev, curr])
        assert result[1].metadata.hierarchy_level.line_type == "header"

    def test_no_align_different_levels(self):
        prev = make_line("ЗАГОЛОВОК", line_type="header", level_1=1, level_2=1)
        curr = make_line("Параграф", line_type="subheader", level_1=1, level_2=2)
        result = extractor._align_same_level_adjacent_header_types([prev, curr])
        assert result[1].metadata.hierarchy_level.line_type == "subheader"
