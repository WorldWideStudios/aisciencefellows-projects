"""Tests for intermediate-dilution planning."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dilution_planner import (  # noqa: E402
    ASSAY, INTERMEDIATE, MEDIUM, STOCK, PipettingSettings, export_transfers_csv, plan_dilutions,
)
from plate_formats import well_name  # noqa: E402
from plate_layout import ROLE_VEHICLE, PlateLayout, StockSolution, WellAssignment  # noqa: E402


def _series_layout(top_um=20.0, factor=2.0, columns=10, replicates=3, stock_mm=10.0):
    layout = PlateLayout("96-well")
    wells = [well_name(r, c) for r in range(replicates) for c in range(1, 1 + columns)]
    layout.apply_dose_series(wells, "Erastin", top_um, "µM", factor)
    layout.stocks["Erastin"] = StockSolution(stock_mm, "mM", "DMSO")
    return layout


def _concentration_in_well(plan, layout, well, well_volume):
    """Recompute the final concentration (nM) in an assay well by following the transfers."""
    stock_nm = layout.stocks["Erastin"].concentration * 1e6
    conc = {i.well: i.concentration for i in plan.intermediates}
    step = next(s for s in plan.assay_steps if s.well == well)
    source = stock_nm if step.source_labware == STOCK else conc[step.source_well]
    return source * step.transfer_ul / well_volume


def test_direct_transfers_when_volume_allows():
    layout = _series_layout(top_um=100, factor=2, columns=2, stock_mm=10)
    plan = plan_dilutions(layout, 100, PipettingSettings(min_transfer_ul=0.5))
    assert not plan.needs_intermediate_plate
    assert {s.source_labware for s in plan.assay_steps} == {STOCK}
    assert plan.assay_steps[0].transfer_ul == pytest.approx(1.0)


def test_small_volumes_use_intermediates_and_hit_targets():
    layout = _series_layout()
    settings = PipettingSettings(min_transfer_ul=1.0, intermediate_transfer_ul=10, dead_volume_ul=20)
    plan = plan_dilutions(layout, 100, settings)
    assert plan.needs_intermediate_plate
    for step in plan.assay_steps:
        assert step.transfer_ul >= settings.min_transfer_ul
        expected = layout.get(step.well).concentration * 1e3
        assert _concentration_in_well(plan, layout, step.well, 100) == pytest.approx(expected)


def test_every_transfer_respects_minimum():
    layout = _series_layout(top_um=10, factor=3, columns=10)
    settings = PipettingSettings(min_transfer_ul=5.0, intermediate_transfer_ul=10)
    plan = plan_dilutions(layout, 100, settings)
    for transfer in plan.transfers:
        assert transfer.volume_ul >= settings.min_transfer_ul - 1e-9


def test_intermediate_volumes_balance():
    layout = _series_layout(top_um=10, factor=3, columns=10)
    settings = PipettingSettings(min_transfer_ul=2.0, intermediate_transfer_ul=10, dead_volume_ul=20)
    plan = plan_dilutions(layout, 100, settings)
    for item in plan.intermediates:
        drawn = sum(t.volume_ul for t in plan.transfers
                    if t.source_labware == INTERMEDIATE and t.source_well == item.well)
        assert item.total_volume_ul >= drawn + settings.dead_volume_ul - 1e-9
        assert item.source_volume_ul + item.medium_volume_ul == pytest.approx(item.total_volume_ul)


def test_very_concentrated_stock_needs_chained_intermediates():
    layout = PlateLayout("96-well")
    layout.assign(["A1"], WellAssignment(drug="Drug", concentration=1, unit="nM"))
    layout.stocks["Drug"] = StockSolution(100, "mM")
    settings = PipettingSettings(min_transfer_ul=1.0, intermediate_transfer_ul=10, dead_volume_ul=20)
    plan = plan_dilutions(layout, 100, settings)
    assert len(plan.intermediates) >= 2
    assert all(t.volume_ul >= 1.0 - 1e-9 for t in plan.transfers)
    step = plan.assay_steps[0]
    conc = {i.well: i.concentration for i in plan.intermediates}
    assert conc[step.source_well] * step.transfer_ul / 100 == pytest.approx(1.0)


def test_transfer_order_and_phases():
    layout = _series_layout()
    plan = plan_dilutions(layout, 100)
    phases = [t.phase for t in plan.transfers]
    assert phases == sorted(phases, key=lambda p: 0 if p == "prepare" else 1)
    assert plan.transfers[0].source_labware == MEDIUM
    assert plan.transfers[-1].dest_labware == ASSAY
    made = set()
    for t in plan.transfers:
        if t.source_labware == INTERMEDIATE:
            assert t.source_well in made
        if t.dest_labware == INTERMEDIATE and t.source_labware != MEDIUM:
            made.add(t.dest_well)


def test_vehicle_matches_highest_solvent_fraction():
    layout = _series_layout()
    layout.assign(["H1", "H2"], WellAssignment(role=ROLE_VEHICLE, drug="DMSO"))
    plan = plan_dilutions(layout, 100)
    vehicle = next(s for s in plan.assay_steps if s.well == "H1")
    assert vehicle.solvent_percent == pytest.approx(0.2)
    assert vehicle.transfer_ul >= 1.0


def test_invalid_settings_raise():
    layout = _series_layout()
    with pytest.raises(ValueError):
        plan_dilutions(layout, 100, PipettingSettings(min_transfer_ul=5, intermediate_transfer_ul=2))


def test_export_transfers_csv(tmp_path):
    plan = plan_dilutions(_series_layout(), 100)
    path = tmp_path / "transfers.csv"
    export_transfers_csv(plan, path)
    with open(path, encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(plan.transfers)
    assert rows[0]["step"] == "1"
