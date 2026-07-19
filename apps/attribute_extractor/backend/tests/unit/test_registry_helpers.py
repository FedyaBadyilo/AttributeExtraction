from __future__ import annotations

from backend.app.services.registry_validation import _cell_str, _synthetic_recpart, _to_int_process_index


def test_to_int_process_index():
    assert _to_int_process_index(0) == 0
    assert _to_int_process_index("1") == 1
    assert _to_int_process_index(1.0) == 1


def test_cell_str_none_for_blank():
    assert _cell_str(None) is None
    assert _cell_str("  ") is None
    assert _cell_str("TU-1") == "TU-1"


def test_synthetic_recpart():
    a = _synthetic_recpart("TZ-1", "basic")
    b = _synthetic_recpart("TZ-1", "basic")
    c = _synthetic_recpart("TZ-1", None)
    assert a == b
    assert a.startswith("SYN-RECPart-")
    assert a != c
