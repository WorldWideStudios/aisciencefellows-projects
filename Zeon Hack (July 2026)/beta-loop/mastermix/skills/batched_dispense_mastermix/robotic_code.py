"""Batched source-to-plate dispense.

Unlike ``cfps_dispense_mastermix``, this aspirates enough liquid for several
destination wells, dispenses the same per-well volume into each, and only ejects
after the batch. This is intended for homogeneous assay setup liquids where a
single tip can safely serve replicate wells.
"""

import json
import math
from datetime import datetime, timezone

from protocol_schema import SkillObject
from utils import (
    PIPETTES,
    attach_next_tip,
    ensure_pipette,
    find_pipettes,
    object_display_name,
    pipette_limits,
    pipette_name,
)

from epipette_aspirate.robotic_code import epipette_aspirate
from epipette_dispense.robotic_code import epipette_dispense
from epipette_eject.robotic_code import epipette_eject

from .modules import ExecutionInfoContext, print_log, project_data_dir


def _rl(msg, kind="event"):
    print_log(msg, runlog=True, runlog_type=kind)


def _preferred_pipette_name(per_well_ul: float) -> str:
    # Keep sub-10 uL compound/control transfers on the 10 uL pipette. The 120 uL
    # pipette starts at 10 uL, so 20/25 uL assay setup transfers go to the large pipette.
    return "epipette_10ul" if float(per_well_ul) < 10.0 else "epipette_120ul"


def _record_timing(condition_label, source_anchor, well, volume_ul):
    if not condition_label:
        return
    run_id = ExecutionInfoContext.get().execution_id or "no_execution"
    ts = datetime.now(timezone.utc).isoformat()
    root = project_data_dir(f"timing/{run_id}", create=True)
    if root is None:
        return
    path = root / "nitrocefin_timing.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {"run_id": run_id, "events": []}
    except Exception:
        data = {"run_id": run_id, "events": []}
    data.setdefault("events", []).append({
        "t0_utc": ts,
        "condition": str(condition_label),
        "well": str(well),
        "source_anchor": str(source_anchor),
        "volume_ul": float(volume_ul),
    })
    path.write_text(json.dumps(data, indent=2) + "\n")
    print_log(
        f"nitrocefin_t0 condition={condition_label} well={well} t0_utc={ts} volume_ul={volume_ul}",
        runlog=True,
        runlog_type="nitrocefin_t0",
    )


def batched_dispense_mastermix(
    pipette: SkillObject,
    tipbox: SkillObject,
    reagent_block: SkillObject,
    reaction_plate: SkillObject,
    mm_anchor: str = "hole_6",
    wells: str = "",
    rxn_volume: float = 20.0,
    num_reactions: int = 0,
    speed: float = 5.0,
    timing_label: str = "",
):
    """Dispense one source into multiple wells, batching wells per aspirate.

    Args:
        pipette: Starting pipette. The skill swaps to the pipette appropriate for
            ``rxn_volume`` if another compatible pipette is present.
        tipbox: Starting tip rack.
        reagent_block: Source object containing the liquid.
        reaction_plate: Destination plate.
        mm_anchor: Source anchor on ``reagent_block``.
        wells: Comma-separated destination wells.
        rxn_volume: Volume to dispense into each destination well, in uL.
        num_reactions: Number of wells to fill from ``wells``.
        speed: Pipette plunger speed.
    """
    print_log(runlog=True, runlog_type="step_start")
    block_name = object_display_name(reagent_block, fallback="source")
    plate_name = object_display_name(reaction_plate, fallback="plate")

    per_well = round(float(rxn_volume), 4)
    num_reactions = int(num_reactions)
    if num_reactions <= 0:
        _rl(f"Skipping batched dispense from {mm_anchor}: num_reactions={num_reactions}")
        return {"success": True, "skipped": True}
    if per_well <= 0:
        raise ValueError(f"batched_dispense_mastermix: rxn_volume must be > 0 uL (got {per_well})")

    well_list = [w.strip() for w in str(wells).replace(";", ",").split(",") if w.strip()]
    targets = well_list[:num_reactions]
    if not targets:
        _rl(f"Skipping batched dispense from {mm_anchor}: no destination wells listed")
        return {"success": True, "skipped": True}
    if len(well_list) < num_reactions:
        _rl(f"Warning: {num_reactions} wells requested but only {len(well_list)} listed; filling {len(targets)}")

    found = find_pipettes() or {pipette_name(pipette): (pipette, tipbox)}
    want = _preferred_pipette_name(per_well)
    selected = found.get(want) or next(iter(found.values()), (pipette, tipbox))
    use_pipette, use_tipbox = selected
    lo, hi = pipette_limits(use_pipette)
    if per_well < lo:
        _rl(f"Warning: {per_well} uL is below {pipette_name(use_pipette)} minimum {lo} uL; attempting anyway")
    if per_well > hi:
        raise ValueError(f"{per_well} uL exceeds {pipette_name(use_pipette)} maximum {hi} uL")

    # Fill as many wells per aspiration as the selected pipette can hold. Leave a
    # little headroom only when it does not cost another batch; exact 100 uL/5x20 uL
    # and 10 uL/2x5 uL batches are intentional for speed.
    wells_per_batch = max(1, int(math.floor(hi / per_well)))
    _rl(
        f"▶ Batched dispense {mm_anchor} ({block_name}) → {plate_name}: {len(targets)} wells @ {per_well} uL "
        f"using {pipette_name(use_pipette)} ({wells_per_batch} well(s) per aspiration)"
    )

    ensure_pipette(use_pipette, found)
    tips_used = 0
    aspirates = 0
    dispenses = 0
    for start in range(0, len(targets), wells_per_batch):
        batch = targets[start:start + wells_per_batch]
        total = round(per_well * len(batch), 4)
        tip = attach_next_tip(use_pipette, use_tipbox)
        tips_used += 1
        aspirates += 1
        _rl(f"  Batch {aspirates}: aspirate {total} uL from {mm_anchor}; dispense {per_well} uL to {batch} (tip #{tip})", "transfer")
        epipette_aspirate(object=reagent_block, anchor=mm_anchor, pipette=use_pipette, volume=total, speed=speed)
        for well in batch:
            epipette_dispense(object=reaction_plate, anchor=well, pipette=use_pipette, volume=per_well, speed=speed)
            dispenses += 1
            _record_timing(timing_label, mm_anchor, well, per_well)
        epipette_eject(pipette=use_pipette)

    _rl(
        f"✓ Batched dispense from {mm_anchor} complete: {len(targets)} wells, {aspirates} aspirate batch(es), "
        f"{dispenses} dispense(s), {tips_used} tip(s)"
    )
    return {"success": True, "tips_used": tips_used, "aspirates": aspirates, "dispenses": dispenses}
