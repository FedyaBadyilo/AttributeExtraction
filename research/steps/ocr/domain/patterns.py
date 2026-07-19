"""Custom dedoc structure patterns for technical specification documents (ТЗ).

Defines five pattern classes that dedoc uses to classify document lines into
hierarchy levels before structure extraction.
"""
import re

from dedoc.data_structures import BoldAnnotation, HierarchyLevel, LineWithMeta
from dedoc.structure_extractors.patterns.abstract_pattern import AbstractPattern

# Numbered paragraph with up to 3 dot-separated components, e.g. "1.", "1.2", "1.2.3".
RULE_PART_REGEX = re.compile(r"^\s*(\d{1,3}\.)+(\d{1,3})?\s*")

# Top-level numbered bold heading, e.g. "1 ВВОДНАЯ ЧАСТЬ" or "1. Введение".
TZ_PART_REGEX = re.compile(r"^(?:\d+\s+|\d+\.\s+[A-Za-zА-Яа-яЁё])")

# Bold numbered sub-heading, e.g. "1.1 Основные положения".
TZ_SUBPART_REGEX = re.compile(r"^\s*\d{1,3}\.\d")


def is_bold(line: LineWithMeta) -> bool:
    """Return True when ≥95 % of non-whitespace characters in the line are bold."""
    bold_annotations = [
        a for a in line.annotations
        if isinstance(a, BoldAnnotation) and a.value == "True"
    ]
    if not bold_annotations:
        return False

    text_no_spaces = re.sub(r"\s+", "", line.line)
    if len(text_no_spaces) == 0:
        return False

    bold_chars = sum(
        len(re.sub(r"\s+", "", line.line[a.start:a.end]))
        for a in bold_annotations
    )
    return bold_chars / len(text_no_spaces) >= 0.95


def is_words(line: LineWithMeta, threshold: float = 0.7) -> bool:
    """Return True when the ratio of alphabetic characters exceeds *threshold*."""
    text_no_spaces = re.sub(r"\s+", "", line.line)
    if not text_no_spaces:
        return False
    letters = sum(1 for c in text_no_spaces if c.isalpha())
    return letters / len(text_no_spaces) > threshold


def is_upper_text(line: LineWithMeta) -> bool:
    """Return True when all alphabetic characters in the line are uppercase."""
    letters = [c for c in line.line.strip() if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


class TzPartPattern(AbstractPattern):
    """Bold numbered top-level heading, e.g. '1 ВВОДНАЯ ЧАСТЬ'."""

    _name = "tz_part"

    def __init__(
        self,
        line_type: str = "tz_part",
        level_1: int = 1,
        level_2: int = 1,
        can_be_multiline: bool = True,
    ) -> None:
        self._line_type = line_type
        self._level_1 = level_1
        self._level_2 = level_2
        self._can_be_multiline = can_be_multiline

    def match(self, line: LineWithMeta) -> bool:
        if not line.line or not line.line.strip():
            return False
        return bool(TZ_PART_REGEX.match(line.line.strip())) and is_bold(line)

    def get_hierarchy_level(self, line: LineWithMeta) -> HierarchyLevel:
        return HierarchyLevel(
            line_type=self._line_type,
            level_1=self._level_1,
            level_2=self._level_2,
            can_be_multiline=self._can_be_multiline,
        )


class TzSubpartPattern(AbstractPattern):
    """Bold numbered sub-heading, e.g. '1.1 Основные положения'."""

    _name = "tz_subpart"

    def __init__(
        self,
        line_type: str = "tz_subpart",
        level_1: int = 1,
        level_2: int = 2,
        can_be_multiline: bool = True,
    ) -> None:
        self._line_type = line_type
        self._level_1 = level_1
        self._level_2 = level_2
        self._can_be_multiline = can_be_multiline

    def match(self, line: LineWithMeta) -> bool:
        if not line.line:
            return False
        return bool(TZ_SUBPART_REGEX.match(line.line.strip())) and is_bold(line)

    def get_hierarchy_level(self, line: LineWithMeta) -> HierarchyLevel:
        return HierarchyLevel(
            line_type=self._line_type,
            level_1=self._level_1,
            level_2=self._level_2,
            can_be_multiline=self._can_be_multiline,
        )


class UppercaseBoldHeaderPattern(AbstractPattern):
    """Bold all-caps header line."""

    _name = "uppercase_header"

    def __init__(
        self,
        line_type: str = "header",
        level_1: int = 1,
        level_2: int = 1,
        can_be_multiline: bool = True,
    ) -> None:
        self._line_type = line_type
        self._level_1 = level_1
        self._level_2 = level_2
        self._can_be_multiline = can_be_multiline

    def match(self, line: LineWithMeta) -> bool:
        if not line.line or not line.line.strip():
            return False
        return is_bold(line) and is_upper_text(line) and is_words(line)

    def get_hierarchy_level(self, line: LineWithMeta) -> HierarchyLevel:
        return HierarchyLevel(
            line_type=self._line_type,
            level_1=self._level_1,
            level_2=self._level_2,
            can_be_multiline=self._can_be_multiline,
        )


class BoldHeaderPattern(AbstractPattern):
    """Generic bold sub-header (not all-caps, not numbered)."""

    _name = "bold_header"

    def __init__(
        self,
        line_type: str = "subheader",
        level_1: int = 1,
        level_2: int = 2,
        can_be_multiline: bool = True,
    ) -> None:
        self._line_type = line_type
        self._level_1 = level_1
        self._level_2 = level_2
        self._can_be_multiline = can_be_multiline

    def match(self, line: LineWithMeta) -> bool:
        if not line.line or not line.line.strip():
            return False
        return is_bold(line) and is_words(line)

    def get_hierarchy_level(self, line: LineWithMeta) -> HierarchyLevel:
        return HierarchyLevel(
            line_type=self._line_type,
            level_1=self._level_1,
            level_2=self._level_2,
            can_be_multiline=self._can_be_multiline,
        )


class RulePartPattern(AbstractPattern):
    """Numbered paragraph, e.g. '1.', '1.2', '1.2.3 Текст'."""

    _name = "rule_part"

    def __init__(
        self,
        line_type: str = "rule_part",
        level_1: int = 2,
        level_2: int = 1,
        can_be_multiline: bool = False,
    ) -> None:
        self._line_type = line_type
        self._level_1 = level_1
        self._level_2 = level_2
        self._can_be_multiline = can_be_multiline

    def match(self, line: LineWithMeta) -> bool:
        return bool(line.line) and bool(RULE_PART_REGEX.match(line.line))

    def get_hierarchy_level(self, line: LineWithMeta) -> HierarchyLevel:
        level_2 = self._level_2
        m = RULE_PART_REGEX.match(line.line)
        if m:
            prefix = m.group(0).strip()
            level_2 = len([n for n in prefix.split(".") if n])
        return HierarchyLevel(
            line_type=self._line_type,
            level_1=self._level_1,
            level_2=level_2,
            can_be_multiline=self._can_be_multiline,
        )


PATTERNS_LIST: list[AbstractPattern] = [
    TzPartPattern(),
    TzSubpartPattern(),
    UppercaseBoldHeaderPattern(),
    BoldHeaderPattern(),
    RulePartPattern(),
]
