from protocol_schema import SkillObject
from utils import attach_next_tip, ensure_pipette, find_pipettes, pipette_for_volume, pipette_limits, pipette_name

from epipette_aspirate.robotic_code import epipette_aspirate
from epipette_dispense.robotic_code import epipette_dispense
from epipette_eject.robotic_code import epipette_eject

from .modules import print_log


def _rl(msg, kind="event"):
    print_log(msg, runlog=True, runlog_type=kind)


def _transfer(found, src_obj, src_anchor, dst_obj, dst_anchor, total_volume, label, speed):
    remaining = round(float(total_volume), 4)
    chunks = 0
    while remaining > 0:
        pipette, tipbox = pipette_for_volume(remaining, found)
        _, hi = pipette_limits(pipette)
        vol = round(min(remaining, hi), 4)
        ensure_pipette(pipette, found)
        tip = attach_next_tip(pipette, tipbox)
        chunks += 1
        _rl(f"  {label}: chunk {chunks} {vol} uL {src_anchor} -> {dst_anchor} ({pipette_name(pipette)}, tip #{tip})", "transfer")
        epipette_aspirate(object=src_obj, anchor=src_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_dispense(object=dst_obj, anchor=dst_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_eject(pipette=pipette)
        remaining = round(remaining - vol, 4)
    return chunks


def _mix(found, obj, anchor, contents_volume, mix_volume, cycles, speed):
    mv = min(float(mix_volume), max(0.5, float(contents_volume) - 1.0))
    pipette, tipbox = pipette_for_volume(mv, found)
    _, hi = pipette_limits(pipette)
    mv = min(mv, hi)
    ensure_pipette(pipette, found)
    tip = attach_next_tip(pipette, tipbox)
    _rl(f"  Mix {anchor}: {cycles} cycles x {mv} uL ({pipette_name(pipette)}, tip #{tip})", "mix")
    for _ in range(max(1, int(cycles))):
        epipette_aspirate(object=obj, anchor=anchor, pipette=pipette, volume=mv, speed=speed)
        epipette_dispense(object=obj, anchor=anchor, pipette=pipette, volume=mv, speed=speed)
    epipette_eject(pipette=pipette)


def prepare_nitrocefin_working_solution(
    pipette: SkillObject,
    tipbox: SkillObject,
    blb_source: SkillObject,
    nitrocefin_stock_source: SkillObject,
    nitrocefin_working_source: SkillObject,
    blb_anchor: str = "hole_7",
    nitrocefin_stock_anchor: str = "hole_4",
    nitrocefin_working_anchor: str = "hole_10",
    nitrocefin_stock_volume_ul: float = 6.25,
    nitrocefin_blb_volume_ul: float = 1243.75,
    mix_volume_ul: float = 100.0,
    mix_cycles: int = 5,
    speed: float = 5.0,
):
    """Prepare 100 uM nitrocefin working solution immediately before use.

    Args:
        nitrocefin_stock_volume_ul: 20 mM nitrocefin stock volume.
        nitrocefin_blb_volume_ul: BLB volume to dilute stock to 100 uM.
    """
    print_log(runlog=True, runlog_type="step_start")
    found = find_pipettes() or {pipette_name(pipette): (pipette, tipbox)}
    total = round(float(nitrocefin_stock_volume_ul) + float(nitrocefin_blb_volume_ul), 4)

    _rl(
        f"▶ Preparing nitrocefin working solution in {nitrocefin_working_anchor}: "
        f"{nitrocefin_stock_volume_ul} uL 20 mM stock + {nitrocefin_blb_volume_ul} uL BLB = {total} uL at 100 uM"
    )
    _transfer(found, blb_source, blb_anchor, nitrocefin_working_source, nitrocefin_working_anchor, nitrocefin_blb_volume_ul, "BLB to nitrocefin", speed)
    _transfer(found, nitrocefin_stock_source, nitrocefin_stock_anchor, nitrocefin_working_source, nitrocefin_working_anchor, nitrocefin_stock_volume_ul, "Nitrocefin stock", speed)
    _mix(found, nitrocefin_working_source, nitrocefin_working_anchor, total, mix_volume_ul, mix_cycles, speed)
    _rl("✓ Nitrocefin working solution ready; proceed immediately to assay wells")
    return {"success": True, "volume_ul": total, "working_concentration_uM": 100.0}
