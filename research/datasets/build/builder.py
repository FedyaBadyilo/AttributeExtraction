from __future__ import annotations

from pathlib import Path

from research.datasets.build import attr_details, ground_truth, io, manifest, nci, rules


def build_dataset(manifest_path: Path, output_dir: Path) -> None:
    examples = manifest.read_manifest(manifest_path)

    gids = [example["gid"] for example in examples]
    mtrs = nci.fetch_mtrs(gids)
    mtr_by_gid = {row["gid"]: row for row in mtrs}

    missing_gids = [gid for gid in gids if gid not in mtr_by_gid]
    if missing_gids:
        raise ValueError(f"MTR cards not found in nci.mtrs for gids: {missing_gids}")

    class_codes = [mtr_by_gid[gid]["class_code"] for gid in gids]
    raw_sets = nci.fetch_class_attribute_sets(class_codes)
    details_by_key = nci.fetch_attr_details(class_codes)
    class_attribute_sets: dict[str, list[dict]] = {}
    for class_code, attrs in raw_sets.items():
        class_attribute_sets[class_code] = [
            rules.apply_extraction_flags(
                attr_details.apply_attr_details(
                    dict(attr),
                    details_by_key.get((class_code, attr["attr_id"])),
                    class_code=class_code,
                )
            )
            for attr in attrs
        ]

    attr_type_by_class = {
        class_code: {attr["attr_id"]: attr["attr_type"] for attr in attrs}
        for class_code, attrs in class_attribute_sets.items()
    }
    gid_to_class = {gid: mtr_by_gid[gid]["class_code"] for gid in gids}

    ground_truth_rows = []
    for row in nci.fetch_ground_truth(gids):
        class_code = gid_to_class[row["gid"]]
        attr_type = attr_type_by_class[class_code].get(row["attr_id"])
        ground_truth_rows.append(
            ground_truth.normalize_ground_truth_row(row, attr_type=attr_type)
        )

    ground_truth_rows = ground_truth.materialize_missing_extraction_slots(
        gid_to_class=gid_to_class,
        class_attribute_sets=class_attribute_sets,
        ground_truth_rows=ground_truth_rows,
    )
    ground_truth.assert_extraction_slots_have_ground_truth(
        gid_to_class=gid_to_class,
        class_attribute_sets=class_attribute_sets,
        ground_truth_rows=ground_truth_rows,
    )

    examples_enriched = [
        {**ex, "class_code": mtr_by_gid[ex["gid"]]["class_code"]}
        for ex in examples
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    io.write_examples_manifest(output_dir / "examples_manifest.json", examples_enriched)
    io.write_class_attribute_sets(output_dir / "class_attribute_sets.json", class_attribute_sets)
    io.write_ground_truth(output_dir / "ground_truth.jsonl", ground_truth_rows)
