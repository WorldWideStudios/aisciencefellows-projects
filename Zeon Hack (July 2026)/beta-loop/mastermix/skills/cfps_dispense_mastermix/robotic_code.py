"""Super-skill: aliquot one built master-mix tube into its reaction wells.

Composes the generic epipette atomics (attach/aspirate/dispense/eject). The
pipette is passed as a SkillObject so it works with epipette_10ul. Dispenses
``rxn_volume`` (default 20 uL) from the mix hole into each destination well,
drawing a fresh tip per stroke and splitting into <=10 uL strokes if needed.
``num_reactions`` <= 0 disables the condition (no-op).

Progress is emitted to the run log at every step via ``print_log(..., runlog=True)``.
"""

import math

from protocol_schema import SkillObject
from utils import (
    attach_next_tip,
    ensure_pipette,
    find_pipettes,
    object_display_name,
    pipette_for_volume,
    pipette_limits,
    pipette_name,
)

from epipette_aspirate.robotic_code import epipette_aspirate
from epipette_dispense.robotic_code import epipette_dispense
from epipette_eject.robotic_code import epipette_eject

from .modules import print_log

def _rl(msg, kind="event"):
    """Emit a run-log line (shown in the run log panel)."""
    print_log(msg, runlog=True, runlog_type=kind)


def _attach_next_tip(tipbox, pipette):
    """Attach the next fresh tip. utils.attach_next_tip advances the counter, rolls
    to the next same-type box when one empties, and pauses for an operator refill
    when all are empty."""
    return attach_next_tip(pipette, tipbox)


def _transfer_chunked(found, src_obj, src_anchor, dst_obj, dst_anchor, total_vol, label="", speed=5.0):
    """Move ``total_vol`` uL from a source anchor to a dest anchor, fresh tip per
    stroke. Picks the pipette from the total volume, swapping if needed, then
    splits into equal strokes within that pipette's range. Returns stroke count."""
    total_vol = round(float(total_vol), 4)
    if total_vol <= 0:
        return 0
    pipette, tipbox = pipette_for_volume(total_vol, found)
    lo, hi = pipette_limits(pipette)
    if total_vol < lo:
        _rl(f"⚠ {label}: {total_vol} uL is below {pipette_name(pipette)}'s {lo} uL minimum — attempting anyway")
    ensure_pipette(pipette, found)
    n_chunks = max(1, math.ceil(total_vol / hi))
    chunk = round(total_vol / n_chunks, 4)
    for i in range(n_chunks):
        vol = chunk if i < n_chunks - 1 else round(total_vol - chunk * (n_chunks - 1), 4)
        tip = _attach_next_tip(tipbox, pipette)
        _rl(f"  {label}: stroke {i + 1}/{n_chunks} — aspirate {vol} uL from {src_anchor} → dispense to {dst_anchor} ({pipette_name(pipette)}, tip #{tip})", "transfer")
        epipette_aspirate(object=src_obj, anchor=src_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_dispense(object=dst_obj, anchor=dst_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_eject(pipette=pipette)
    return n_chunks


def cfps_dispense_mastermix(
    pipette: SkillObject,
    tipbox: SkillObject,
    reagent_block: SkillObject,
    reaction_plate: SkillObject,
    mm_anchor: str = "hole_6",
    wells: str = "",
    rxn_volume: float = 20.0,
    num_reactions: int = 0,
    speed: float = 5.0,
):
    """Aliquot a master-mix tube into its reaction wells (fresh tip per stroke).

    Args:
        pipette: The held pipette (e.g. epipette_10ul).
        tipbox: Tip rack to draw fresh tips from.
        reagent_block: Cold block holding the master-mix tube.
        reaction_plate: Destination well plate.
        mm_anchor: hole holding the built master mix.
        wells: comma-separated destination wells (e.g. "A3,A4"); the first
            ``num_reactions`` are filled.
        rxn_volume: volume per well in uL; split into <=10 uL strokes if needed.
        num_reactions: <= 0 disables (no-op).
        speed: pipette plunger speed.
    """
    print_log(runlog=True, runlog_type="step_start")
    block_name = object_display_name(reagent_block, fallback="cold block")
    plate_name = object_display_name(reaction_plate, fallback="plate")

    num_reactions = int(num_reactions)
    if num_reactions <= 0:
        _rl(f"⏭ Skipping dispense from {mm_anchor}: num_reactions={num_reactions} (condition disabled)")
        return {"success": True, "skipped": True}

    well_list = [w.strip() for w in str(wells).replace(";", ",").split(",") if w.strip()]
    if not well_list:
        _rl(f"⏭ No wells listed for {mm_anchor}; nothing to dispense")
        return {"success": True, "skipped": True}

    targets = well_list[:num_reactions]
    if len(well_list) < num_reactions:
        _rl(f"⚠ {num_reactions} reactions requested but only {len(well_list)} wells listed; filling {len(targets)}")
    _rl(f"▶ Dispensing {mm_anchor} ({block_name}) → {plate_name} wells {targets} @ {rxn_volume} uL each")

    found = find_pipettes() or {pipette_name(pipette): (pipette, tipbox)}

    tips_used = 0
    strokes_used = 0
    for idx, well in enumerate(targets, 1):
        _rl(f"  ● Well {idx}/{len(targets)}: {well} ← {rxn_volume} uL from {mm_anchor}")
        k = _transfer_chunked(found, reagent_block, mm_anchor, reaction_plate, well, float(rxn_volume), label=f"{mm_anchor}→{well}", speed=speed)
        tips_used += k
        strokes_used += k

    _rl(f"✓ Dispense from {mm_anchor} complete ({len(targets)} well(s)) — used {tips_used} tips, {strokes_used} aspirate/dispense strokes")
    return {"success": True, "tips_used": tips_used, "strokes_used": strokes_used}
