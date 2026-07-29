"""Plan stage: picks the next round's conditions and writes them as a workflow
input preset, for either of the two experimental round types.

Split in two layers on purpose:
  - Plain functions (`plan_kinetics_round`, `plan_inhibitor_round`) do the actual
    numeric/scientific decision-making. They need no LLM and no credentials, so
    they're what the rest of the pipeline (and tests) call directly.
  - An ADK `Agent` wraps them as tools, for the case where a human wants to steer
    Plan conversationally ("try a narrower dose range around compound X's last
    IC50") rather than always taking the deterministic default.

Placeholder numbers throughout (default concentration ranges, assumed stock
concentrations) are flagged PLACEHOLDER — swap for real values from the protein
scientist / the real compound library CSV without touching the wiring around them.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from google.adk.agents import Agent

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
import beads_writer as bw  # noqa: E402
INPUTS_DIR = PROJECT_ROOT / "inputs"
LIBRARY_CSV = PROJECT_ROOT / "pipeline" / "library" / "compounds.csv"

# 96-well scan order (A1, A2, ... H12) used to hand out plate positions in order.
_ROWS = "ABCDEFGH"
WELL_ORDER = [f"{r}{c}" for r in _ROWS for c in range(1, 13)]

# --- kinetics round -----------------------------------------------------------

# PLACEHOLDER default grid — matches tem1_kinetics_characterization.json's 3x3 +
# 2-blank layout (pt_e{1..3}s{1..3}, blank_e, blank_s). Replace with real ranges.
DEFAULT_ENZYME_NM = [10.0, 50.0, 250.0]
DEFAULT_NITROCEFIN_UM = [50.0, 150.0, 450.0]
DEFAULT_TOTAL_WELL_VOLUME_UL = 20.0
# The tubes this bench actually draws from, per
# tem1_kinetics_dilution_and_dosing_calculations.pdf: a single enzyme_hole (EZ3)
# and a single substrate_hole (NC4), reused for every leg — there is no per-point
# tube swapping in the workflow graph, so concentration comes from volume alone.
ENZYME_STOCK_NM = 5.5363     # EZ3, 0.16 ng/uL
NITROCEFIN_STOCK_UM = 125.0  # NC4

# The deck's single 10 uL epipette. `epipette_aspirate` is one plunger stroke per
# call with no auto-chunking, so a leg outside this range is not a rounding issue
# — it is a leg the hardware cannot pipette.
PIPETTE_MIN_UL = 0.5
PIPETTE_MAX_UL = 10.0


def _dilution_vol(target_conc: float, stock_conc: float, total_vol_ul: float) -> float:
    """uL of stock needed in `total_vol_ul` to hit `target_conc`, given `stock_conc`."""
    if target_conc <= 0:
        return 0.0
    return round(target_conc * total_vol_ul / stock_conc, 3)


def plan_kinetics_round(
    enzyme_levels_nm: list[float] | None = None,
    nitrocefin_levels_um: list[float] | None = None,
    total_well_volume_ul: float = DEFAULT_TOTAL_WELL_VOLUME_UL,
) -> dict:
    """Build the full input-value dict for tem1_kinetics_characterization.json.

    3x3 enzyme x nitrocefin grid plus an enzyme-only and a nitrocefin-only blank,
    wells handed out in plate scan order starting at A1.
    """
    enzyme_levels_nm = enzyme_levels_nm or DEFAULT_ENZYME_NM
    nitrocefin_levels_um = nitrocefin_levels_um or DEFAULT_NITROCEFIN_UM
    if len(enzyme_levels_nm) != 3 or len(nitrocefin_levels_um) != 3:
        raise ValueError("tem1_kinetics_characterization.json's graph is fixed at a 3x3 grid")

    values: dict = {
        "reagent_block": "coldblock_wellplate",
        "reaction_plate": "wellplate_96_flatbottom",
        "enzyme_hole": "hole_1",
        "substrate_hole": "hole_2",
        "buffer_hole": "hole_3",
        "total_well_volume_ul": total_well_volume_ul,
        "run_name": "tem1_kinetics_run",
    }

    wells = iter(WELL_ORDER)
    tip = 1
    for i, e_conc in enumerate(enzyme_levels_nm, start=1):
        for j, s_conc in enumerate(nitrocefin_levels_um, start=1):
            pos = f"pt_e{i}s{j}"
            well = next(wells)
            enz_vol = _dilution_vol(e_conc, ENZYME_STOCK_NM, total_well_volume_ul)
            sub_vol = _dilution_vol(s_conc, NITROCEFIN_STOCK_UM, total_well_volume_ul)
            buf_vol = round(total_well_volume_ul - enz_vol - sub_vol, 3)
            values[f"{pos}_well"] = well
            values[f"{pos}_enzyme_vol_ul"] = enz_vol
            values[f"{pos}_enzyme_tip_index"] = tip
            values[f"{pos}_substrate_vol_ul"] = sub_vol
            values[f"{pos}_substrate_tip_index"] = tip + 1
            values[f"{pos}_buffer_vol_ul"] = max(buf_vol, 0.0)
            values[f"{pos}_buffer_tip_index"] = tip + 2
            tip += 3

    # blank_e: mid enzyme level, no nitrocefin. blank_s: mid nitrocefin level, no enzyme.
    mid_e, mid_s = enzyme_levels_nm[1], nitrocefin_levels_um[1]
    for blank_name, vol, hole_label in [
        ("blank_e", _dilution_vol(mid_e, ENZYME_STOCK_NM, total_well_volume_ul), "enz"),
        ("blank_s", _dilution_vol(mid_s, NITROCEFIN_STOCK_UM, total_well_volume_ul), "sub"),
    ]:
        well = next(wells)
        buf_vol = round(total_well_volume_ul - vol, 3)
        values[f"{blank_name}_well"] = well
        values[f"{blank_name}_vol_ul"] = vol
        values[f"{blank_name}_tip_index"] = tip
        values[f"{blank_name}_buffer_vol_ul"] = max(buf_vol, 0.0)
        values[f"{blank_name}_buffer_tip_index"] = tip + 1
        tip += 2

    return values


def _check_leg(label: str, vol_ul: float) -> None:
    """A leg is either not pipetted at all, or within one stroke of the epipette."""
    if vol_ul == 0:
        return
    if not (PIPETTE_MIN_UL <= vol_ul <= PIPETTE_MAX_UL):
        raise ValueError(
            f"{label} = {vol_ul} uL is outside the epipette's {PIPETTE_MIN_UL}-{PIPETTE_MAX_UL} uL "
            "single-stroke range — the hardware cannot pipette this leg"
        )


def plan_kinetics_round_by_volume(
    enzyme_vols_ul: list[float] | None = None,
    substrate_vols_ul: list[float] | None = None,
    total_well_volume_ul: float = DEFAULT_TOTAL_WELL_VOLUME_UL,
    blank_vol_ul: float = 10.0,
) -> dict:
    """Build the kinetics input preset from *volumes* rather than target
    concentrations — the form a dosing table from the protocol doc is written in.

    Same 3x3 grid, wells, and tip order as `plan_kinetics_round`; only the way the
    volumes are arrived at differs. Buffer tops each well up to
    `total_well_volume_ul`, and every leg is checked against the pipette's real
    range before it can become a workflow default, so a misread row fails here
    rather than on the deck.

    Reports the resulting in-well concentrations so the caller can check them
    against whatever the source document claims.
    """
    enzyme_vols_ul = enzyme_vols_ul or [5.0, 7.0, 9.0]
    substrate_vols_ul = substrate_vols_ul or [5.0, 7.0, 9.0]
    if len(enzyme_vols_ul) != 3 or len(substrate_vols_ul) != 3:
        raise ValueError("tem1_kinetics_characterization.json's graph is fixed at a 3x3 grid")

    values: dict = {
        "reagent_block": "coldblock_wellplate",
        "reaction_plate": "wellplate_96_flatbottom",
        "enzyme_hole": "hole_1",
        "substrate_hole": "hole_2",
        "buffer_hole": "hole_3",
        "total_well_volume_ul": total_well_volume_ul,
        "run_name": "tem1_kinetics_run",
    }
    concentrations = {}

    wells = iter(WELL_ORDER)
    tip = 1
    for i, e_vol in enumerate(enzyme_vols_ul, start=1):
        for j, s_vol in enumerate(substrate_vols_ul, start=1):
            pos = f"pt_e{i}s{j}"
            buf_vol = round(total_well_volume_ul - e_vol - s_vol, 3)
            _check_leg(f"{pos} enzyme", e_vol)
            _check_leg(f"{pos} substrate", s_vol)
            _check_leg(f"{pos} buffer", buf_vol)
            if buf_vol < 0:
                raise ValueError(
                    f"{pos}: enzyme {e_vol} + substrate {s_vol} exceeds the "
                    f"{total_well_volume_ul} uL well"
                )
            well = next(wells)
            values[f"{pos}_well"] = well
            values[f"{pos}_enzyme_vol_ul"] = e_vol
            values[f"{pos}_enzyme_tip_index"] = tip
            values[f"{pos}_substrate_vol_ul"] = s_vol
            values[f"{pos}_substrate_tip_index"] = tip + 1
            values[f"{pos}_buffer_vol_ul"] = buf_vol
            values[f"{pos}_buffer_tip_index"] = tip + 2
            concentrations[pos] = {
                "well": well,
                "enzyme_nm": round(ENZYME_STOCK_NM * e_vol / total_well_volume_ul, 4),
                "nitrocefin_um": round(NITROCEFIN_STOCK_UM * s_vol / total_well_volume_ul, 4),
            }
            tip += 3

    # blank_e: enzyme, no substrate. blank_s: substrate, no enzyme. Each has two
    # legs summing to the well volume, so the split is forced once blank_vol is set.
    for blank_name in ("blank_e", "blank_s"):
        buf_vol = round(total_well_volume_ul - blank_vol_ul, 3)
        _check_leg(f"{blank_name} reagent", blank_vol_ul)
        _check_leg(f"{blank_name} buffer", buf_vol)
        well = next(wells)
        values[f"{blank_name}_well"] = well
        values[f"{blank_name}_vol_ul"] = blank_vol_ul
        values[f"{blank_name}_tip_index"] = tip
        values[f"{blank_name}_buffer_vol_ul"] = buf_vol
        values[f"{blank_name}_buffer_tip_index"] = tip + 1
        concentrations[blank_name] = {"well": well, "vol_ul": blank_vol_ul}
        tip += 2

    values["_concentrations"] = concentrations
    values["_stocks"] = {"enzyme_nm": ENZYME_STOCK_NM, "nitrocefin_um": NITROCEFIN_STOCK_UM}
    return values


# --- inhibitor_dose_response round ---------------------------------------------

DEFAULT_DOSE_COUNT = 8
# PLACEHOLDER — used only until a kinetics round has a real fit to read.
DEFAULT_NITROCEFIN_VOL_UL = 5.0


def load_compound_library(path: Path = LIBRARY_CSV) -> list[dict]:
    """Read the compound library CSV. Expected columns: compound_id, source_well,
    stock_conc_um (at minimum) — schema is a placeholder until the real file lands;
    this is the only function that would need to change to match it.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"compound library not found at {path} — drop the real CSV there "
            "(columns: compound_id, source_well, stock_conc_um)"
        )
    with path.open() as f:
        return list(csv.DictReader(f))


def next_compound(library: list[dict], already_screened: set[str]) -> dict | None:
    for row in library:
        if row["compound_id"] not in already_screened:
            return row
    return None


def _log_spaced(center: float, n: int, span_decades: float = 2.0) -> list[float]:
    """n concentrations log-spaced +/- span_decades/2 around `center`."""
    import math

    if n < 2:
        return [center]
    lo, hi = -span_decades / 2, span_decades / 2
    return [round(center * (10 ** (lo + (hi - lo) * k / (n - 1))), 4) for k in range(n)]


def plan_inhibitor_round(
    compound: dict,
    expressed_wells: list[str],
    prior_ic50_um: float | None = None,
    nitrocefin_vol_ul: float = DEFAULT_NITROCEFIN_VOL_UL,
    compound_stock_um: float | None = None,
) -> dict:
    """Build the full input-value dict for cfps_inhibitor_dose_response.json.

    Doses up to 8 of `expressed_wells` (already-confirmed TEM1 wells from a
    cfps_expression round) with a log-spaced concentration series of `compound`,
    centered on `prior_ic50_um` if a previous round fit one, else a broad default.
    """
    n = min(DEFAULT_DOSE_COUNT, len(expressed_wells))
    if n == 0:
        raise ValueError("need at least one confirmed expressed well to dose")

    center = prior_ic50_um if prior_ic50_um and prior_ic50_um > 0 else 10.0  # PLACEHOLDER default center
    target_concs_um = _log_spaced(center, n)
    stock_um = compound_stock_um or float(compound.get("stock_conc_um", 1000.0))
    total_vol_ul = DEFAULT_TOTAL_WELL_VOLUME_UL  # dosed into an already-full CFPS well; small volume assumed

    values: dict = {
        "reagent_block": "coldblock_wellplate",
        "reaction_plate": "wellplate_96_flatbottom",
        "compound_library": "wellplate_pcr_parts_2",
        "platereader": "plate_reader",
        "plate_home": "wellplate_holder_tags",
        "nitrocefin_hole": "hole_9",
        "compound_id": compound["compound_id"],
        "dose_n": n,
        "run_name": f"cfps_inhibitor_dose_response_{compound['compound_id']}",
    }
    for i in range(n):
        pos = i + 1
        vol = _dilution_vol(target_concs_um[i], stock_um, total_vol_ul)
        values[f"dose{pos}_well"] = expressed_wells[i]
        values[f"dose{pos}_compound_src_well"] = compound["source_well"]
        values[f"dose{pos}_compound_vol_ul"] = vol
        values[f"dose{pos}_compound_tip_index"] = pos
        values[f"dose{pos}_nitrocefin_vol_ul"] = nitrocefin_vol_ul
        values[f"dose{pos}_nitrocefin_tip_index"] = pos + 8

    return values


# --- shared: write the preset + create the beads round -------------------------

def write_round_inputs(round_id: str, values: dict) -> Path:
    INPUTS_DIR.mkdir(exist_ok=True)
    # `run_name` is how watch_execution matches a physical run back to its round,
    # so it has to be unique per round — the per-assay-type base name alone would
    # make a second round of the same type claim the first one's execution.
    values = {**values, "run_name": f"{values['run_name']}_{round_id}"}
    out_path = INPUTS_DIR / f"{round_id}.json"
    out_path.write_text(json.dumps({"_label": round_id, **values}, indent=2) + "\n")
    return out_path


def plan_and_record_kinetics_round(**kwargs) -> bw.Round:
    values = plan_kinetics_round(**kwargs)
    round_ = bw.create_round("kinetics", objective="TEM1 kinetics characterization")
    write_round_inputs(round_.id, values)
    return round_


def plan_and_record_kinetics_round_by_volume(**kwargs) -> bw.Round:
    values = plan_kinetics_round_by_volume(**kwargs)
    round_ = bw.create_round("kinetics", objective="TEM1 kinetics characterization")
    write_round_inputs(round_.id, values)
    return round_


def plan_and_record_inhibitor_round(**kwargs) -> bw.Round:
    values = plan_inhibitor_round(**kwargs)
    compound_id = kwargs["compound"]["compound_id"]
    round_ = bw.create_round(
        "inhibitor_dose_response",
        objective=f"Inhibitor dose response — {compound_id}",
        compound_id=compound_id,
    )
    write_round_inputs(round_.id, values)
    return round_


# --- ADK agent wrapper -----------------------------------------------------------

def plan_kinetics_round_tool(
    enzyme_levels_nm: list[float] = None,
    nitrocefin_levels_um: list[float] = None,
) -> dict:
    """Plan a kinetics characterization round: purified TEM1 x nitrocefin grid.

    Call with no arguments for the default coarse grid, or pass exactly 3 enzyme
    levels (nM) and 3 nitrocefin levels (uM) to try a specific range. Creates the
    beads round bead and writes its input preset; returns the round id.
    """
    round_ = plan_and_record_kinetics_round(
        enzyme_levels_nm=enzyme_levels_nm, nitrocefin_levels_um=nitrocefin_levels_um,
    )
    return {"round_id": round_.id, "assay_type": round_.assay_type}


def plan_kinetics_round_by_volume_tool(
    enzyme_vols_ul: list[float] = None,
    substrate_vols_ul: list[float] = None,
    total_well_volume_ul: float = 20.0,
    blank_vol_ul: float = 10.0,
) -> dict:
    """Plan a kinetics round from an explicit per-leg dosing table — the form a
    protocol document states it in — instead of from target concentrations.

    Pass the 3 enzyme leg volumes and 3 substrate leg volumes in uL; the grid is
    their cross product, buffer tops each well up to total_well_volume_ul, and
    wells/tip indices are assigned in plate scan and execution order. Every leg is
    validated against the epipette's 0.5-10 uL single-stroke range and raises if a
    transcribed number is unrunnable.

    Returns the round id plus the in-well concentrations the volumes work out to,
    so they can be checked against what the source document claims.
    """
    round_ = plan_and_record_kinetics_round_by_volume(
        enzyme_vols_ul=enzyme_vols_ul,
        substrate_vols_ul=substrate_vols_ul,
        total_well_volume_ul=total_well_volume_ul,
        blank_vol_ul=blank_vol_ul,
    )
    preset = json.loads((INPUTS_DIR / f"{round_.id}.json").read_text())
    return {
        "round_id": round_.id,
        "assay_type": round_.assay_type,
        "concentrations": preset["_concentrations"],
        "stocks": preset["_stocks"],
    }


def plan_inhibitor_round_tool(
    compound_id: str,
    expressed_wells: list[str],
    prior_ic50_um: float = None,
) -> dict:
    """Plan an inhibitor dose-response round for one compound from the library.

    `expressed_wells` are wells on the current CFPS plate already confirmed
    (go/no-go, cfps_expression round) to hold expressed TEM1. Pass `prior_ic50_um`
    to center the dose series on a previous round's fit; omit it for a broad
    default range. Creates the beads round bead and writes its input preset;
    returns the round id.
    """
    library = load_compound_library()
    compound = next((r for r in library if r["compound_id"] == compound_id), None)
    if compound is None:
        raise ValueError(f"compound_id {compound_id!r} not found in {LIBRARY_CSV}")
    round_ = plan_and_record_inhibitor_round(
        compound=compound, expressed_wells=expressed_wells, prior_ic50_um=prior_ic50_um,
    )
    return {"round_id": round_.id, "assay_type": round_.assay_type}


root_agent = Agent(
    name="plan_agent",
    model="gemini-2.5-flash",
    description="Plans the next round of the TEM1 CFPS screening campaign.",
    instruction=(
        "You plan rounds for a TEM1 beta-lactamase screening campaign that runs on a Zeon "
        "lab-automation project. There are two round types you can plan:\n"
        "1. kinetics — a prerequisite, standalone purified-enzyme x nitrocefin-substrate "
        "characterization. Plan this first if none has been run yet (call "
        "plan_kinetics_round_tool with no arguments for the default grid, or with a "
        "narrower range if the operator asks for one).\n"
        "2. inhibitor_dose_response — a compound dose-response screen against expressed "
        "TEM1. Only plan this once the operator confirms a kinetics round is decided and "
        "tells you which wells on the current plate are confirmed-expressed. Pick the next "
        "unscreened compound unless the operator names one, and pass any prior IC50 you're "
        "told about to center the dose series.\n"
        "Always report back the round_id a tool call returns — that's what the operator "
        "uses to find its input preset under inputs/<round_id>.json and follow it through "
        "Simulate and Approve."
    ),
    tools=[plan_kinetics_round_tool, plan_inhibitor_round_tool],
)
