"""Simulation-based checks of the dilution planner on fixed and random layouts."""

import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dilution_planner import PipettingSettings, plan_dilutions  # noqa: E402
from plan_checker import check_plan  # noqa: E402
from plate_formats import well_name  # noqa: E402
from plate_layout import (  # noqa: E402
    CONCENTRATION_UNITS, ROLE_POSITIVE, ROLE_TREATMENT, ROLE_UNTREATED, ROLE_VEHICLE,
    PlateLayout, StockSolution, WellAssignment, from_nanomolar, to_nanomolar,
)
from verify_plan import example_layout  # noqa: E402


@pytest.mark.parametrize("min_transfer", [0.5, 1.0, 2.0, 5.0])
def test_example_layout_passes(min_transfer):
    layout = example_layout()
    settings = PipettingSettings(min_transfer_ul=min_transfer)
    plan = plan_dilutions(layout, 100, settings)
    report = check_plan(layout, plan, 100, settings)
    assert report.passed, (report.problems, [w for w in report.wells if not w.ok][:5])


def _random_layout(seed: int) -> tuple[PlateLayout, float, PipettingSettings]:
    rng = random.Random(seed)
    format_name = rng.choice(["24-well", "96-well", "384-well"])
    layout = PlateLayout(format_name)
    fmt = layout.plate_format
    wells = [well_name(r, c) for r in range(fmt.rows) for c in range(fmt.columns)]
    rng.shuffle(wells)
    volume = fmt.default_working_volume_ul
    settings = PipettingSettings(
        min_transfer_ul=rng.choice([0.5, 1.0, 2.0, 5.0]),
        intermediate_transfer_ul=rng.choice([5.0, 10.0]) if volume > 10 else 5.0,
        dead_volume_ul=rng.choice([10.0, 20.0, 50.0]),
    )
    if settings.intermediate_transfer_ul < settings.min_transfer_ul:
        settings.intermediate_transfer_ul = settings.min_transfer_ul

    for index in range(rng.randint(1, 4)):
        drug = f"Drug{index}"
        stock_nm = to_nanomolar(rng.choice([1, 10, 50, 100]), "mM")
        layout.stocks[drug] = StockSolution(from_nanomolar(stock_nm, "mM"), "mM", rng.choice(["DMSO", "Water"]))
        for _ in range(rng.randint(1, 12)):
            if not wells:
                break
            target_nm = stock_nm / 10 ** rng.uniform(0.5, 7)
            unit = rng.choice(CONCENTRATION_UNITS)
            count = rng.randint(1, 4)
            chosen, wells = wells[:count], wells[count:]
            layout.assign(chosen, WellAssignment(rng.choice([ROLE_TREATMENT, ROLE_POSITIVE]), drug,
                                                 from_nanomolar(target_nm, unit), unit))
    for role, drug in ((ROLE_VEHICLE, "DMSO"), (ROLE_UNTREATED, "")):
        chosen, wells = wells[:3], wells[3:]
        layout.assign(chosen, WellAssignment(role, drug))
    return layout, volume, settings


@pytest.mark.parametrize("seed", range(300))
def test_random_layouts_pass(seed):
    layout, volume, settings = _random_layout(seed)
    plan = plan_dilutions(layout, volume, settings)
    report = check_plan(layout, plan, volume, settings)
    assert all(w.ok for w in report.wells), [w for w in report.wells if not w.ok][:5]
    assert not report.problems, report.problems


def test_checker_catches_a_wrong_volume():
    layout = example_layout()
    plan = plan_dilutions(layout, 100)
    dose = next(t for t in plan.transfers if t.phase == "dose" and t.dest_well == "A5")
    dose.volume_ul *= 1.1
    report = check_plan(layout, plan, 100)
    assert not report.passed
    assert any(w.well == "A5" and not w.ok for w in report.wells)


def test_checker_catches_a_wrong_source():
    layout = example_layout()
    plan = plan_dilutions(layout, 100)
    doses = [t for t in plan.transfers if t.phase == "dose" and t.source_labware == "intermediate"]
    doses[0].source_well, doses[1].source_well = doses[1].source_well, doses[0].source_well
    assert not check_plan(layout, plan, 100).passed
