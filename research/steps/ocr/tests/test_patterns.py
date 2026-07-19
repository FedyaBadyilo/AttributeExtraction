"""Unit tests for dedoc pattern classifiers in patterns.py."""
import pytest

from research.steps.ocr.domain.patterns import (
    BoldHeaderPattern,
    RULE_PART_REGEX,
    RulePartPattern,
    TzPartPattern,
    TzSubpartPattern,
    UppercaseBoldHeaderPattern,
    is_bold,
    is_upper_text,
    is_words,
)
from research.steps.ocr.tests.fixtures import make_line


# ---------------------------------------------------------------------------
# is_bold
# ---------------------------------------------------------------------------

class TestIsBold:
    def test_fully_bold_line(self):
        line = make_line("ЗАГОЛОВОК", bold=True)
        assert is_bold(line) is True

    def test_not_bold_line(self):
        line = make_line("обычный текст", bold=False)
        assert is_bold(line) is False

    def test_empty_line(self):
        line = make_line("", bold=False)
        assert is_bold(line) is False


# ---------------------------------------------------------------------------
# is_words / is_upper_text
# ---------------------------------------------------------------------------

class TestIsWords:
    def test_word_line(self):
        line = make_line("Привет мир")
        assert is_words(line) is True

    def test_numeric_line(self):
        # Nearly no alphabetic characters
        line = make_line("123456789")
        assert is_words(line) is False


class TestIsUpperText:
    def test_all_caps(self):
        line = make_line("ВВОДНАЯ ЧАСТЬ")
        assert is_upper_text(line) is True

    def test_mixed_case(self):
        line = make_line("Вводная часть")
        assert is_upper_text(line) is False

    def test_no_letters(self):
        line = make_line("1234")
        assert is_upper_text(line) is False


# ---------------------------------------------------------------------------
# RULE_PART_REGEX
# ---------------------------------------------------------------------------

class TestRulePartRegex:
    @pytest.mark.parametrize("text", ["1.", "1.2", "1.2.3", "  1.2.3  ", "10.20"])
    def test_matches(self, text: str):
        assert RULE_PART_REGEX.match(text) is not None

    @pytest.mark.parametrize("text", ["abc", "1234.12345", ""])
    def test_no_match(self, text: str):
        assert RULE_PART_REGEX.match(text) is None


# ---------------------------------------------------------------------------
# Pattern: TzPartPattern
# ---------------------------------------------------------------------------

class TestTzPartPattern:
    pattern = TzPartPattern()

    def test_matches_numbered_bold_heading(self):
        line = make_line("1 ВВОДНАЯ ЧАСТЬ", bold=True)
        assert self.pattern.match(line) is True

    def test_no_match_not_bold(self):
        line = make_line("1 ВВОДНАЯ ЧАСТЬ", bold=False)
        assert self.pattern.match(line) is False

    def test_no_match_no_number(self):
        line = make_line("ВВОДНАЯ ЧАСТЬ", bold=True)
        assert self.pattern.match(line) is False

    def test_hierarchy_level(self):
        line = make_line("1 ВВОДНАЯ ЧАСТЬ", bold=True)
        hl = self.pattern.get_hierarchy_level(line)
        assert hl.line_type == "tz_part"
        assert hl.level_1 == 1
        assert hl.level_2 == 1


# ---------------------------------------------------------------------------
# Pattern: TzSubpartPattern
# ---------------------------------------------------------------------------

class TestTzSubpartPattern:
    pattern = TzSubpartPattern()

    def test_matches_bold_subpart(self):
        line = make_line("1.1 Основные положения", bold=True)
        assert self.pattern.match(line) is True

    def test_no_match_not_bold(self):
        line = make_line("1.1 Основные положения", bold=False)
        assert self.pattern.match(line) is False

    def test_no_match_top_level(self):
        line = make_line("1 Основные положения", bold=True)
        assert self.pattern.match(line) is False


# ---------------------------------------------------------------------------
# Pattern: UppercaseBoldHeaderPattern
# ---------------------------------------------------------------------------

class TestUppercaseBoldHeaderPattern:
    pattern = UppercaseBoldHeaderPattern()

    def test_matches_bold_uppercase(self):
        line = make_line("ОБЩИЕ ТРЕБОВАНИЯ", bold=True)
        assert self.pattern.match(line) is True

    def test_no_match_mixed_case(self):
        line = make_line("Общие требования", bold=True)
        assert self.pattern.match(line) is False

    def test_no_match_empty(self):
        line = make_line("", bold=True)
        assert self.pattern.match(line) is False


# ---------------------------------------------------------------------------
# Pattern: BoldHeaderPattern
# ---------------------------------------------------------------------------

class TestBoldHeaderPattern:
    pattern = BoldHeaderPattern()

    def test_matches_bold_words(self):
        line = make_line("Основные положения", bold=True)
        assert self.pattern.match(line) is True

    def test_no_match_not_bold(self):
        line = make_line("Основные положения", bold=False)
        assert self.pattern.match(line) is False


# ---------------------------------------------------------------------------
# Pattern: RulePartPattern — level_2 from prefix depth
# ---------------------------------------------------------------------------

class TestRulePartPattern:
    pattern = RulePartPattern()

    def test_matches_single_number(self):
        line = make_line("1. текст требования")
        assert self.pattern.match(line) is True

    def test_level_2_from_depth(self):
        line_1 = make_line("1. текст")
        line_2 = make_line("1.2 текст")
        line_3 = make_line("1.2.3 текст")
        assert self.pattern.get_hierarchy_level(line_1).level_2 == 1
        assert self.pattern.get_hierarchy_level(line_2).level_2 == 2
        assert self.pattern.get_hierarchy_level(line_3).level_2 == 3

    def test_no_match_plain_text(self):
        line = make_line("просто текст без номера")
        assert self.pattern.match(line) is False
