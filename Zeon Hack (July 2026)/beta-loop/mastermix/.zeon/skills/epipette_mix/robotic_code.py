from protocol_schema import SkillObject
from utils import epipette_device, object_display_name
import time

from .modules import epipette_aspirate, epipette_dispense, print_log

MAX_PIPETTE_VOL_UL = 10.0
MIN_PIPETTE_VOL_UL = 0.5


def _rl(msg, kind="event"):
    """Emit a run-log line (shown in the run log panel)."""
    print_log(msg, runlog=True, runlog_type=kind)


def epipette_mix(
    pipette: SkillObject,
    mix_volume: float,
    contents_volume: float,
    cycles: int = 5,
    speed: float = 1.0,
):
    """Mix a well/tube in place: aspirate and dispense repeatedly, NO arm motion.

    The caller must have already lowered the tip into the liquid; this skill only
    works the pipette (it never moves the arm or the gripper). It draws
    ``mix_volume`` up and pushes it back out ``cycles`` times by calling the
    aspirate/dispense execution functions directly. Each cycle is
    aspirate-then-dispense, so the tip starts and ends empty and it slots in cleanly
    after a descent, before a tip eject.

    ``mix_volume`` MUST be smaller than ``contents_volume`` — the amount added into
    the container. You cannot mix more liquid than is present without the tip
    drawing air, so a ``mix_volume`` at or above ``contents_volume`` raises
    ValueError. It is also capped at the pipette maximum.

    Args:
        pipette: The held pipette (arm already in place; used only for logging —
            this skill does not move it).
        mix_volume: Volume (uL) drawn and expelled each cycle. Must be strictly less
            than ``contents_volume``; capped at the pipette max.
        contents_volume: Total volume (uL) present in the container (what was added
            into it) — the hard upper bound ``mix_volume`` must stay under.
        cycles: Number of aspirate/dispense trituration cycles (clamped to >= 1).
        speed: Plunger speed.
    """
    print_log(runlog=True, runlog_type="step_start")
    pip_name = object_display_name(pipette, fallback="pipette")

    mv = round(float(mix_volume), 4)
    cv = round(float(contents_volume), 4)

    if mv <= 0:
        raise ValueError(f"epipette_mix: mix_volume must be > 0 uL (got {mv}).")
    if cv <= 0:
        raise ValueError(f"epipette_mix: contents_volume must be > 0 uL (got {cv}).")
    if mv >= cv:
        raise ValueError(
            f"epipette_mix: mix_volume ({mv} uL) must be smaller than the contents "
            f"volume ({cv} uL) added into the container."
        )
    if mv > MAX_PIPETTE_VOL_UL:
        _rl(f"⚠ epipette_mix: mix_volume {mv} uL exceeds pipette max {MAX_PIPETTE_VOL_UL} uL — capping to {MAX_PIPETTE_VOL_UL}.")
        mv = MAX_PIPETTE_VOL_UL
    if mv < MIN_PIPETTE_VOL_UL:
        _rl(f"⚠ epipette_mix: mix_volume {mv} uL is below the {MIN_PIPETTE_VOL_UL} uL pipette minimum — attempting anyway.")

    cycles = max(1, int(cycles))
    _rl(f"↻ Mixing {pip_name} in place: {cycles} cycles of {mv} uL (contents {cv} uL) — no arm motion")

    # Aspirate then dispense in place. No arm motion — the tip stays where the
    # caller left it, submerged in the liquid.
    for c in range(cycles):
        print_log(f"  mix cycle {c + 1}/{cycles}: aspirate/dispense {mv} uL in place")
        epipette_aspirate(name=epipette_device(pipette), volume=mv, speed=speed)
        time.sleep(0.5)
        epipette_dispense(name=epipette_device(pipette), volume=mv, speed=speed)
        time.sleep(0.5)

    _rl(f"✓ epipette_mix complete: {cycles} cycles of {mv} uL")
    return {"success": True, "cycles": cycles, "mix_volume": mv}
