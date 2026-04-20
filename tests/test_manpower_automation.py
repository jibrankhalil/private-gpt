from scripts.manpower_automation import SheetColumns, aggregate, col_to_index


def test_col_to_index() -> None:
    assert col_to_index("A") == 0
    assert col_to_index("F") == 5
    assert col_to_index("AA") == 26


def test_aggregate_counts_and_locations() -> None:
    columns = SheetColumns(
        name="B",
        driver_type="F",
        status="H",
        location="I",
        team="J",
    )
    rows = [
        ["", "Ali", "", "", "", "LB", "", "OD", "Rig-1", "OpsA"],
        ["", "Ben", "", "", "", "HB", "", "Sick", "Camp", "OpsA"],
        ["", "Cara", "", "", "", "LB", "", "On Duty", "Rig-1", "OpsB"],
    ]

    result = aggregate(rows, columns, {"on duty": "OD", "od": "OD"})

    assert result["total_people"] == 3
    assert result["type_counts"]["LB"] == 2
    assert result["type_counts"]["HB"] == 1
    assert result["status_counts"]["OD"] == 2
    assert result["status_counts"]["Sick"] == 1
    assert sorted(result["location_people"]["Rig-1"]) == ["Ali", "Cara"]
