from __future__ import annotations

import pytest

from research.datasets.build.ground_truth import (
    assert_extraction_slots_have_ground_truth,
    is_empty_ground_truth_value,
    materialize_missing_extraction_slots,
    normalize_ground_truth_row,
    parse_nci_range_value,
)


def test_empty_ground_truth_placeholders() -> None:
    for value in (None, "", "   ", "-", "—", " -‡- ", "n/a", "Н/Д"):
        assert is_empty_ground_truth_value(value)


def test_non_empty_ground_truth_value() -> None:
    assert not is_empty_ground_truth_value("0‡300")
    assert not is_empty_ground_truth_value("4")


def test_normalize_ground_truth_row_clears_empty_value() -> None:
    row = {"gid": 1, "attr_id": "a1", "attr_name": "Attr", "value": "-"}

    assert normalize_ground_truth_row(row) == {
        "gid": 1,
        "attr_id": "a1",
        "attr_name": "Attr",
        "value": None,
    }
    assert row["value"] == "-"


def test_parse_nci_range_value() -> None:
    assert parse_nci_range_value("0,12‡0,12") == [0.12, 0.12]
    assert parse_nci_range_value("00‡300") == [0.0, 300.0]
    assert parse_nci_range_value("0‡70") == [0.0, 70.0]
    assert parse_nci_range_value("400") == [400.0, 400.0]
    assert parse_nci_range_value("0,7") == [0.7, 0.7]


def test_normalize_ground_truth_row_parses_range() -> None:
    row = {
        "gid": 1,
        "attr_id": "attr6526",
        "attr_name": "Мощность привода",
        "value": "0,12‡0,12",
    }

    assert normalize_ground_truth_row(row, attr_type="Диапазон") == {
        "gid": 1,
        "attr_id": "attr6526",
        "attr_name": "Мощность привода",
        "value": [0.12, 0.12],
    }


def test_normalize_ground_truth_row_parses_scalar_range() -> None:
    row = {
        "gid": 1318719,
        "attr_id": "attr1805",
        "attr_name": "Ширина",
        "value": "400",
    }

    assert normalize_ground_truth_row(row, attr_type="Диапазон") == {
        "gid": 1318719,
        "attr_id": "attr1805",
        "attr_name": "Ширина",
        "value": [400.0, 400.0],
    }


def test_normalize_ground_truth_row_keeps_non_range_value() -> None:
    row = {"gid": 1, "attr_id": "a1", "attr_name": "Attr", "value": "0,12‡0,12"}

    assert normalize_ground_truth_row(row, attr_type="Строка") == row


def test_assert_extraction_slots_have_ground_truth_ok() -> None:
    assert_extraction_slots_have_ground_truth(
        gid_to_class={1: "180198"},
        class_attribute_sets={
            "180198": [
                {
                    "attr_id": "attr1620",
                    "attr_name": "Диаметр номинальный DN",
                    "for_extraction": True,
                },
                {
                    "attr_id": "attr9999",
                    "attr_name": "Excluded",
                    "for_extraction": False,
                },
            ]
        },
        ground_truth_rows=[
            {"gid": 1, "attr_id": "attr1620", "attr_name": "DN", "value": None},
        ],
    )


def test_assert_extraction_slots_have_ground_truth_missing() -> None:
    with pytest.raises(ValueError, match="Missing ground truth for 1 for_extraction"):
        assert_extraction_slots_have_ground_truth(
            gid_to_class={760506: "180198"},
            class_attribute_sets={
                "180198": [
                    {
                        "attr_id": "attr1620",
                        "attr_name": "Диаметр номинальный DN",
                        "for_extraction": True,
                    }
                ]
            },
            ground_truth_rows=[],
        )


def test_materialize_missing_extraction_slots() -> None:
    rows = materialize_missing_extraction_slots(
        gid_to_class={1: "180198"},
        class_attribute_sets={
            "180198": [
                {
                    "attr_id": "attr1620",
                    "attr_name": "Диаметр номинальный DN",
                    "for_extraction": True,
                },
                {
                    "attr_id": "attr8449",
                    "attr_name": "Назначение",
                    "for_extraction": True,
                },
                {
                    "attr_id": "attr9999",
                    "attr_name": "Excluded",
                    "for_extraction": False,
                },
            ]
        },
        ground_truth_rows=[
            {"gid": 1, "attr_id": "attr1620", "attr_name": "DN", "value": "100"},
        ],
    )

    assert rows == [
        {"gid": 1, "attr_id": "attr1620", "attr_name": "DN", "value": "100"},
        {
            "gid": 1,
            "attr_id": "attr8449",
            "attr_name": "Назначение",
            "value": None,
        },
    ]
    assert_extraction_slots_have_ground_truth(
        gid_to_class={1: "180198"},
        class_attribute_sets={
            "180198": [
                {
                    "attr_id": "attr1620",
                    "attr_name": "Диаметр номинальный DN",
                    "for_extraction": True,
                },
                {
                    "attr_id": "attr8449",
                    "attr_name": "Назначение",
                    "for_extraction": True,
                },
                {
                    "attr_id": "attr9999",
                    "attr_name": "Excluded",
                    "for_extraction": False,
                },
            ]
        },
        ground_truth_rows=rows,
    )
