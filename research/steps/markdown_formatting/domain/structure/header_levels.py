from research.steps.ocr.domain.patterns import PATTERNS_LIST


def get_header_level_mapping() -> dict[str, int]:
    result: dict[str, int] = {}
    for pattern in PATTERNS_LIST:
        level_1 = pattern._level_1
        if level_1 != 1:
            continue
        line_type = pattern._line_type
        level_2 = pattern._level_2
        result[line_type] = level_2
    return result


def get_list_level_mapping() -> dict[str, int]:
    result: dict[str, int] = {}
    for pattern in PATTERNS_LIST:
        level_1 = pattern._level_1
        if level_1 != 2:
            continue
        line_type = pattern._line_type
        level_2 = pattern._level_2
        result[line_type] = level_2
    return result


HEADER_LEVEL_MAPPING = get_header_level_mapping()
LIST_LEVEL_MAPPING = get_list_level_mapping()


def get_level_1(paragraph_type: str) -> int | None:
    """Return 1 for header types, 2 for list types, None otherwise."""
    if paragraph_type in HEADER_LEVEL_MAPPING:
        return 1
    if paragraph_type in LIST_LEVEL_MAPPING:
        return 2
    return None


def is_header_type(paragraph_type: str) -> bool:
    return paragraph_type in HEADER_LEVEL_MAPPING


def is_list_type(paragraph_type: str) -> bool:
    return paragraph_type in LIST_LEVEL_MAPPING
