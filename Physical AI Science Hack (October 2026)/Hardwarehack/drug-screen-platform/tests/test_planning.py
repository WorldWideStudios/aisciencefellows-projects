"""Tests for the shared plan-and-check helper."""

from plate_layout import PlateLayout
from planning import plan_layout, well_volume
from verify_plan import example_layout


def test_well_volume_defaults_to_format_working_volume():
    assert well_volume(PlateLayout("96-well")) == 100


def test_well_volume_reads_saved_value():
    layout = PlateLayout("96-well")
    layout.pipetting["well_volume_ul"] = 150
    assert well_volume(layout) == 150


def test_plan_layout_example_passes():
    result = plan_layout(example_layout())
    assert result.report.passed
    assert len(result.plan.transfers) == 128
    assert result.volume_ul == 100


def test_saved_well_volume_survives_round_trip(tmp_path):
    layout = example_layout()
    layout.pipetting["well_volume_ul"] = 150
    layout.save_json(tmp_path / "plate.json")
    assert well_volume(PlateLayout.load_json(tmp_path / "plate.json")) == 150


def test_min_transfer_defaults_to_pipette_minimum():
    result = plan_layout(example_layout())
    assert result.settings.min_transfer_ul == 5
    assert min(t.volume_ul for t in result.plan.transfers) >= 5


def test_saved_min_transfer_is_kept():
    layout = example_layout()
    layout.pipetting["min_transfer_ul"] = 10
    assert plan_layout(layout).settings.min_transfer_ul == 10
