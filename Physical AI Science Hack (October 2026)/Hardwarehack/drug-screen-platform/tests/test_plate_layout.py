"""Tests for plate formats and the plate layout model."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from plate_formats import PLATE_FORMATS, parse_well, row_label, well_name  # noqa: E402
from plate_layout import PlateLayout, StockSolution, WellAssignment  # noqa: E402


def test_well_counts():
    expected = {"6-well": 6, "12-well": 12, "24-well": 24, "48-well": 48,
                "96-well": 96, "384-well": 384, "1536-well": 1536}
    for name, count in expected.items():
        assert PLATE_FORMATS[name].well_count == count


def test_row_labels_round_trip():
    assert row_label(0) == "A"
    assert row_label(15) == "P"
    assert row_label(31) == "AF"
    for row in range(32):
        for col in (0, 47):
            assert parse_well(well_name(row, col)) == (row, col)


def test_assign_rejects_wells_outside_plate():
    layout = PlateLayout("96-well")
    with pytest.raises(ValueError):
        layout.assign(["I1"], WellAssignment(drug="X"))
    with pytest.raises(ValueError):
        layout.assign(["A13"], WellAssignment(drug="X"))


def test_dose_series_along_rows():
    layout = PlateLayout("96-well")
    wells = [well_name(r, c) for r in range(2) for c in range(4)]
    layout.apply_dose_series(wells, "Erastin", 10, "µM", 2, direction="row")
    assert [layout.get(f"A{c}").concentration for c in range(1, 5)] == [10, 5, 2.5, 1.25]
    assert layout.get("B4").concentration == 1.25


def test_dose_series_along_columns():
    layout = PlateLayout("96-well")
    layout.apply_dose_series(["A1", "B1", "C1"], "RSL3", 1, "µM", 10, direction="column")
    assert [layout.get(w).concentration for w in ("A1", "B1", "C1")] == [1, 0.1, 0.01]


def test_change_format_drops_out_of_range_wells():
    layout = PlateLayout("384-well")
    layout.assign(["A1", "P24"], WellAssignment(drug="X", concentration=1))
    dropped = layout.change_format("96-well")
    assert dropped == ["P24"]
    assert layout.get("A1") is not None


def test_json_round_trip(tmp_path):
    layout = PlateLayout("384-well", "Screen 1")
    layout.apply_dose_series(["A1", "A2"], "Drug", 10, "µM", 3)
    layout.stocks["Drug"] = StockSolution(10, "mM")
    layout.pipetting = {"min_transfer_ul": 5.0}
    path = tmp_path / "plate.json"
    layout.save_json(path)
    loaded = PlateLayout.load_json(path)
    assert loaded.name == "Screen 1"
    assert loaded.format_name == "384-well"
    assert loaded.get("A2").concentration == pytest.approx(3.333)
    assert loaded.stocks["Drug"].concentration == 10
    assert loaded.pipetting == {"min_transfer_ul": 5.0}


def test_load_invalid_file(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    with pytest.raises(ValueError):
        PlateLayout.load_json(path)


def test_layout_csv_has_every_well(tmp_path):
    layout = PlateLayout("24-well")
    layout.assign(["B3"], WellAssignment(drug="X", concentration=5, unit="nM"))
    path = tmp_path / "layout.csv"
    layout.export_layout_csv(path)
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    b3 = next(r for r in rows if r["well"] == "B3")
    assert (b3["row"], b3["column"], b3["drug"], b3["unit"]) == ("B", "3", "X", "nM")
