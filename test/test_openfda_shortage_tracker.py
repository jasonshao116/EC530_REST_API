from srcs.openfda_shortage_tracker import build_snapshot, diff_snapshots, normalize_record


def test_normalize_record_uses_fallback_keys():
    record = {
        "shortage_id": "S-100",
        "generic_name": "Example Drug",
        "shortage_status": "Current",
        "reason_for_shortage": "Manufacturing delay",
    }

    normalized = normalize_record(record)

    assert normalized["key"] == "S-100"
    assert normalized["drug_name"] == "Example Drug"
    assert normalized["status"] == "Current"
    assert normalized["reason"] == "Manufacturing delay"


def test_diff_snapshots_detects_added_removed_changed():
    old_records = [
        {"id": "1", "drug_name": "Drug A", "status": "Current"},
        {"id": "2", "drug_name": "Drug B", "status": "Current"},
    ]
    new_records = [
        {"id": "1", "drug_name": "Drug A", "status": "Resolved"},
        {"id": "3", "drug_name": "Drug C", "status": "Current"},
    ]

    old_snapshot = build_snapshot(old_records)
    new_snapshot = build_snapshot(new_records)
    diff = diff_snapshots(old_snapshot, new_snapshot)

    assert [item["key"] for item in diff.added] == ["3"]
    assert [item["key"] for item in diff.removed] == ["2"]
    assert [item["key"] for item in diff.changed] == ["1"]
    assert diff.changed[0]["before"]["status"] == "Current"
    assert diff.changed[0]["after"]["status"] == "Resolved"