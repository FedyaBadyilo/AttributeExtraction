from __future__ import annotations

from backend.app.services.exporting.normalize import normalize_value


def test_normalize_number():
    assert normalize_value("1,5", "number") == 1.5
    assert normalize_value(" 2 ", "number") == 2


def test_normalize_bool():
    assert normalize_value("да", "bool") is True
    assert normalize_value("нет", "bool") is False


def test_normalize_string_strip():
    assert normalize_value("  x  ", "string") == "x"
