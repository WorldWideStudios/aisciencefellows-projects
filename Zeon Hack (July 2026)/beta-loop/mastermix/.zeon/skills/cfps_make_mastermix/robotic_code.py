"""Super-skill: build one CFPS master-mix tube for a single condition.

Composes the generic epipette atomics (attach/aspirate/dispense/eject). Every
reagent volume is batched by the tube size (num_reactions x per-well volume + a
fixed dead-volume overage). Each transfer picks its own pipette from that total
volume — under 10 uL the 10 uL pipette, otherwise the 120 uL one — swapping on
the stand when needed, and is only split into multiple strokes if it exceeds
that pipette's maximum. Reagents are ordered so the run starts with whichever
pipette is already in hand, which costs at most one swap per tube. A fresh tip is
drawn per stroke from the rack matching the pipette. After the tube is built it
is homogenised in place by repeated aspirate/dispense (no centrifuge).

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
    pipette_in_hand,
    pipette_limits,
    pipette_name,
)

from epipette_aspirate.robotic_code import epipette_aspirate
from epipette_dispense.robotic_code import epipette_dispense
from epipette_eject.robotic_code import epipette_eject
from epipette_mix.robotic_code import epipette_mix

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
    """Move ``total_vol`` uL from a source anchor to a dest anchor.

    Picks the pipette from the total volume (before splitting, so a 20 uL
    transfer is one 120 uL stroke rather than two 10 uL ones) and swaps to it if
    it isn't already held. Splits into EQUAL strokes within that pipette's range
    (not greedy) so the final stroke never drops below its minimum. A fresh tip
    is attached and ejected for each stroke; each stroke is logged.
    """
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
        # Last stroke absorbs any rounding remainder so the strokes sum exactly.
        vol = chunk if i < n_chunks - 1 else round(total_vol - chunk * (n_chunks - 1), 4)
        tip = _attach_next_tip(tipbox, pipette)
        _rl(f"  {label}: stroke {i + 1}/{n_chunks} — aspirate {vol} uL from {src_anchor} → dispense to {dst_anchor} ({pipette_name(pipette)}, tip #{tip})", "transfer")
        epipette_aspirate(object=src_obj, anchor=src_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_dispense(object=dst_obj, anchor=dst_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_eject(pipette=pipette)
    return n_chunks


def cfps_make_mastermix(
    pipette: SkillObject,
    tipbox: SkillObject,
    reagent_block: SkillObject,
    extract_anchor: str = "hole_1",
    buffer_anchor: str = "hole_2",
    dna_anchor: str = "hole_3",
    water_anchor: str = "hole_5",
    mm_anchor: str = "hole_6",
    extract_per_rxn: float = 3.0,
    buffer_per_rxn: float = 4.0,
    dna_per_rxn: float = 0.0,
    water_per_rxn: float = 3.0,
    rxn_volume_ul: float = 20.0,
    recipe_ref_ul: float = 10.0,
    num_reactions: int = 0,
    extra_volume_ul: float = 10.0,
    mix_cycles: int = 5,
    mix_volume: float = 8.0,
    speed: float = 5.0,
):
    """Build one master-mix tube for a condition, batched and homogenised.

    Args:
        pipette: The held pipette (e.g. epipette_10ul).
        tipbox: Tip rack to draw fresh tips from.
        reagent_block: Cold block holding the reagent tubes AND the mix tube.
        extract_anchor, buffer_anchor, dna_anchor, water_anchor: source holes.
        mm_anchor: destination hole where this master mix is built.
        extract_per_rxn, buffer_per_rxn, dna_per_rxn, water_per_rxn: component
            volume (uL) per reference reaction (they should sum to recipe_ref_ul).
            The robot pipettes Extract/Buffer/Water only; DNA is assumed PRE-LOADED
            in the mix tube by the operator (its volume is logged, not pipetted), so
            dna_anchor is retained for reference but not used for a transfer.
        rxn_volume_ul: the volume dispensed per destination well. The reference
            recipe is scaled by rxn_volume_ul / recipe_ref_ul so concentrations are
            preserved at any well volume (e.g. 20 uL well = kit 10 uL recipe x2).
        recipe_ref_ul: total volume the *_per_rxn values are defined for (10 uL).
        num_reactions: reactions/wells to serve; <= 0 means this condition is
            disabled and the skill no-ops.
        extra_volume_ul: small fixed dead-volume overage (uL) added to the tube on
            top of num_reactions x rxn_volume_ul (default 10 uL, not a whole reaction).
        mix_cycles, mix_volume: in-place trituration after the tube is built.
        speed: pipette plunger speed.
    """
    print_log(runlog=True, runlog_type="step_start")
    block_name = object_display_name(reagent_block, fallback="cold block")

    num_reactions = int(num_reactions)
    if num_reactions <= 0:
        _rl(f"⏭ Skipping master mix at {mm_anchor}: num_reactions={num_reactions} (condition disabled)")
        return {"success": True, "skipped": True}

    extra_volume_ul = max(0.0, float(extra_volume_ul))
    ref = float(recipe_ref_ul) or 10.0
    scale = float(rxn_volume_ul) / ref  # per-well recipe scale (for display)
    dispensed = round(num_reactions * float(rxn_volume_ul), 4)
    tube_total = round(dispensed + extra_volume_ul, 4)  # small fixed overage, NOT a whole extra reaction
    comp_scale = tube_total / ref  # scale the reference recipe (sums to ref uL) to the whole tube
    _rl(
        f"▶ Building master mix in {block_name}/{mm_anchor}: {num_reactions} well(s) x {rxn_volume_ul} uL "
        f"= {dispensed} uL + {extra_volume_ul} uL extra → {tube_total} uL tube"
    )

    # DNA (control/sample) is PRE-LOADED into the mix tube by the operator before the
    # run — the per-reaction volume is too small to pipette reliably — so the robot
    # never transfers it. Log the amount that must already be present in the tube.
    dna_total = round(float(dna_per_rxn) * comp_scale, 4) if float(dna_per_rxn) > 0 else 0.0
    if dna_total > 0:
        _rl(f"  ⓘ Assumes {dna_total} uL DNA is pre-loaded in {mm_anchor} (operator adds it before the run)")

    # Reagents the robot pipettes from source holes.
    reagents = [
        ("Extract", extract_anchor, float(extract_per_rxn)),
        ("Buffer", buffer_anchor, float(buffer_per_rxn)),
        ("Water", water_anchor, float(water_per_rxn)),
    ]

    # Order by volume, starting from whichever pipette is already in hand. Since
    # the 10 uL cutoff is itself a volume threshold, one sorted pass puts all the
    # big-pipette reagents on one side and all the small-pipette ones on the
    # other — so pointing that run at the held pipette costs at most one swap.
    found = find_pipettes() or {pipette_name(pipette): (pipette, tipbox)}
    held = pipette_in_hand(found)
    small_first = held is not None and pipette_name(held) == "epipette_10ul"
    reagents.sort(key=lambda r: r[2], reverse=not small_first)
    tips_used = 0
    strokes_used = 0
    for name, src_anchor, per_rxn in reagents:
        if per_rxn <= 0:
            _rl(f"  – {name}: none in this mix, skipping")
            continue
        per_well = round(per_rxn * scale, 4)
        total = round(per_rxn * comp_scale, 4)  # (per_rxn / ref) x tube volume
        _rl(f"  ● {name}: {per_well} uL/well, {total} uL total ({src_anchor} → {mm_anchor})")
        k = _transfer_chunked(found, reagent_block, src_anchor, reagent_block, mm_anchor, total, label=name, speed=speed)
        tips_used += k
        strokes_used += k

    # Homogenise the tube in place (no centrifuge). Descend into the liquid ONCE via
    # the full aspirate skill as a POSITIONING move only (volume=0, no draw; it does
    # not retract), then delegate the mixing to the epipette_mix skill, so the arm
    # stays put in the well between cycles instead of re-approaching.
    #
    # Mix with whatever pipette the transfers left in hand, clamped to its range
    # — the 120 uL pipette can't do the 8 uL default, so it mixes at its 10 uL
    # minimum instead. No swap just to mix.
    mix_pipette, mix_tipbox = found.get(pipette_name(pipette_in_hand(found) or pipette)) or (pipette, tipbox)
    mix_lo, mix_hi = pipette_limits(mix_pipette)
    mv = round(max(mix_lo, min(float(mix_volume), mix_hi)), 4)
    cycles = max(1, int(mix_cycles))
    _rl(f"  ↻ Mixing {mm_anchor}: {cycles} plunger cycles of {mv} uL in place with {pipette_name(mix_pipette)} (no centrifuge)")
    _attach_next_tip(mix_tipbox, mix_pipette)
    tips_used += 1
    epipette_aspirate(object=reagent_block, anchor=mm_anchor, pipette=mix_pipette, volume=0.0, speed=speed)  # descend only, no draw
    epipette_mix(pipette=mix_pipette, mix_volume=mv, contents_volume=tube_total, cycles=cycles, speed=speed)
    strokes_used += cycles
    epipette_eject(pipette=mix_pipette)

    _rl(f"✓ Master mix at {mm_anchor} complete (~{tube_total} uL for {num_reactions} well(s)) — used {tips_used} tips, {strokes_used} aspirate/dispense strokes")
    return {"success": True, "tips_used": tips_used, "strokes_used": strokes_used}
