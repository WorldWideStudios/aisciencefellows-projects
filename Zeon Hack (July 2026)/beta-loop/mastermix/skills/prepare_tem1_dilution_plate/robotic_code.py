from protocol_schema import SkillObject
from utils import attach_next_tip, ensure_pipette, find_pipettes, pipette_for_volume, pipette_limits, pipette_name

from batched_dispense_mastermix.robotic_code import batched_dispense_mastermix
from epipette_aspirate.robotic_code import epipette_aspirate
from epipette_dispense.robotic_code import epipette_dispense
from epipette_eject.robotic_code import epipette_eject

from .modules import print_log


def _rl(msg, kind="event"):
    print_log(msg, runlog=True, runlog_type=kind)


def _transfer_one(found, src_obj, src_anchor, dst_obj, dst_anchor, volume, label, speed):
    pipette, tipbox = found.get("epipette_10ul") or next(iter(found.values()))
    ensure_pipette(pipette, found)
    tip = attach_next_tip(pipette, tipbox)
    _rl(f"  {label}: {volume} uL {src_anchor} -> {dst_anchor} ({pipette_name(pipette)}, tip #{tip})", "transfer")
    epipette_aspirate(object=src_obj, anchor=src_anchor, pipette=pipette, volume=volume, speed=speed)
    epipette_dispense(object=dst_obj, anchor=dst_anchor, pipette=pipette, volume=volume, speed=speed)
    epipette_eject(pipette=pipette)


def _transfer_chunked(found, src_obj, src_anchor, dst_obj, dst_anchor, total_volume, label, speed):
    remaining = round(float(total_volume), 4)
    if remaining <= 0:
        return 0
    chunks = 0
    while remaining > 0:
        pipette, tipbox = pipette_for_volume(remaining, found)
        _, hi = pipette_limits(pipette)
        vol = round(min(remaining, hi), 4)
        ensure_pipette(pipette, found)
        tip = attach_next_tip(pipette, tipbox)
        chunks += 1
        _rl(f"  {label}: chunk {chunks} aspirate/dispense {vol} uL {src_anchor} -> {dst_anchor} ({pipette_name(pipette)}, tip #{tip})", "transfer")
        epipette_aspirate(object=src_obj, anchor=src_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_dispense(object=dst_obj, anchor=dst_anchor, pipette=pipette, volume=vol, speed=speed)
        epipette_eject(pipette=pipette)
        remaining = round(remaining - vol, 4)
    return chunks


def _mix_well(found, plate, well, contents_volume, mix_volume, cycles, speed):
    pipette, tipbox = found.get("epipette_10ul") or next(iter(found.values()))
    ensure_pipette(pipette, found)
    tip = attach_next_tip(pipette, tipbox)
    mv = min(float(mix_volume), max(0.5, float(contents_volume) - 1.0), 10.0)
    _rl(f"  Mix {well}: {cycles} cycles x {mv} uL ({pipette_name(pipette)}, tip #{tip})", "mix")
    for _ in range(max(1, int(cycles))):
        epipette_aspirate(object=plate, anchor=well, pipette=pipette, volume=mv, speed=speed)
        epipette_dispense(object=plate, anchor=well, pipette=pipette, volume=mv, speed=speed)
    epipette_eject(pipette=pipette)


def _mix_container(found, obj, anchor, contents_volume, mix_volume, cycles, speed):
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


def prepare_tem1_dilution_plate(
    pipette: SkillObject,
    tipbox: SkillObject,
    blb_source: SkillObject,
    dmso_source: SkillObject,
    working_plate: SkillObject,
    tem1_stock_source: SkillObject,
    positive_source_plate: SkillObject,
    compound_1_source_plate: SkillObject,
    compound_2_source_plate: SkillObject,
    compound_3_source_plate: SkillObject,
    compound_4_source_plate: SkillObject,
    compound_5_source_plate: SkillObject,
    compound_6_source_plate: SkillObject,
    compound_7_source_plate: SkillObject,
    compound_8_source_plate: SkillObject,
    blb_anchor: str = "hole_5",
    blb_anchor_2: str = "hole_6",
    dmso_anchor: str = "hole_9",
    tem1_stock_anchor: str = "hole_1",
    tem1_intermediate_anchor: str = "hole_2",
    tazobactam_intermediate_anchor: str = "hole_3",
    tem1_working_anchor: str = "hole_8",
    positive_source_well: str = "H7",

    # positive_dest_well: str = "A1",
    # vehicle_dest_well: str = "A2",
    # compound_1_source_well: str = "G6",
    # compound_1_dest_well: str = "A3",
    # compound_2_source_well: str = "F2",
    # compound_2_dest_well: str = "A4",
    # compound_3_source_well: str = "B10",
    # compound_3_dest_well: str = "A5",
    # compound_4_source_well: str = "F7",
    # compound_4_dest_well: str = "A6",
    # compound_5_source_well: str = "A10",
    # compound_5_dest_well: str = "A7",
    # compound_6_source_well: str = "B10",
    # compound_6_dest_well: str = "A8",
    # compound_7_source_well: str = "B4",
    # compound_7_dest_well: str = "A9",
    # compound_8_source_well: str = "H8",
    # compound_8_dest_well: str = "A10",
    positive_dest_well: str = "A1",
    vehicle_dest_well: str = "A2",
    compound_1_source_well: str = "B10",
    compound_1_dest_well: str = "A3",
    compound_2_source_well: str = "F2",
    compound_2_dest_well: str = "A4",
    compound_3_source_well: str = "F7",
    compound_3_dest_well: str = "A5",
    compound_4_source_well: str = "A9",
    compound_4_dest_well: str = "A6",
    compound_5_source_well: str = "A3",
    compound_5_dest_well: str = "A7",
    compound_6_source_well: str = "A4",
    compound_6_dest_well: str = "A8",
    compound_7_source_well: str = "A2",
    compound_7_dest_well: str = "A9",
    compound_8_source_well: str = "F3",
    compound_8_dest_well: str = "A10",

    
    stock_volume_ul: float = 2.5,
    compound_blb_volume_ul: float = 47.5,
    vehicle_dmso_volume_ul: float = 5.0,
    vehicle_blb_volume_ul: float = 95.0,
    tem1_stock_volume_ul: float = 2.0,
    tem1_step1_blb_volume_ul: float = 198.0,
    tem1_intermediate_volume_ul: float = 100.0,
    tem1_step2_blb_volume_ul: float = 900.0,
    tem1_mix_volume_ul: float = 100.0,
    tazobactam_stock_volume_ul: float = 1.0,
    tazobactam_intermediate_blb_volume_ul: float = 49.0,
    mix_volume_ul: float = 10.0,
    mix_cycles: int = 5,
    speed: float = 5.0,
):
    """Prepare working solutions for the current TEM-1 single-plate screen.

    Each compound/control well receives 2.5 uL of 10 mM stock + 47.5 uL BLB,
    producing 50 uL at 500 uM. The vehicle well receives 5 uL DMSO + 95 uL BLB,
    producing 100 uL at 5% DMSO.
    """
    print_log(runlog=True, runlog_type="step_start")
    found = find_pipettes() or {pipette_name(pipette): (pipette, tipbox)}

    working_solutions = [
        ("Positive control", positive_source_plate, positive_source_well, positive_dest_well),
        ("Compound 1", compound_1_source_plate, compound_1_source_well, compound_1_dest_well),
        ("Compound 2", compound_2_source_plate, compound_2_source_well, compound_2_dest_well),
        ("Compound 3", compound_3_source_plate, compound_3_source_well, compound_3_dest_well),
        ("Compound 4", compound_4_source_plate, compound_4_source_well, compound_4_dest_well),
        ("Compound 5", compound_5_source_plate, compound_5_source_well, compound_5_dest_well),
        ("Compound 6", compound_6_source_plate, compound_6_source_well, compound_6_dest_well),
        ("Compound 7", compound_7_source_plate, compound_7_source_well, compound_7_dest_well),
        ("Compound 8", compound_8_source_plate, compound_8_source_well, compound_8_dest_well),
    ]
    working_solutions = [s for s in working_solutions if str(s[2]).strip() and str(s[3]).strip()]
    compound_dests = [dest for _, _, _, dest in working_solutions]

    _rl("▶ Preparing purified TEM-1 working solution: 100 ng/uL stock -> 1 ng/uL intermediate -> 0.1 ng/uL working solution")
    _transfer_one(found, tem1_stock_source, tem1_stock_anchor, blb_source, tem1_intermediate_anchor, float(tem1_stock_volume_ul), "TEM-1 stock to intermediate", speed)
    _transfer_chunked(found, blb_source, blb_anchor_2, blb_source, tem1_intermediate_anchor, float(tem1_step1_blb_volume_ul), "BLB to TEM-1 intermediate", speed)
    _mix_container(found, blb_source, tem1_intermediate_anchor, float(tem1_stock_volume_ul) + float(tem1_step1_blb_volume_ul), tem1_mix_volume_ul, mix_cycles, speed)
    _transfer_chunked(found, blb_source, tem1_intermediate_anchor, blb_source, tem1_working_anchor, float(tem1_intermediate_volume_ul), "TEM-1 intermediate to working", speed)
    _transfer_chunked(found, blb_source, blb_anchor_2, blb_source, tem1_working_anchor, float(tem1_step2_blb_volume_ul), "BLB to TEM-1 working", speed)
    _mix_container(found, blb_source, tem1_working_anchor, float(tem1_intermediate_volume_ul) + float(tem1_step2_blb_volume_ul), tem1_mix_volume_ul, mix_cycles, speed)

    _rl("▶ Preparing T1262 tazobactam 200 uM intermediate for 1 uM assay condition")
    _transfer_chunked(found, blb_source, blb_anchor, blb_source, tazobactam_intermediate_anchor, float(tazobactam_intermediate_blb_volume_ul), "BLB to T1262 intermediate", speed)
    _transfer_one(found, compound_1_source_plate, compound_1_source_well, blb_source, tazobactam_intermediate_anchor, float(tazobactam_stock_volume_ul), "T1262 stock to intermediate", speed)
    _mix_container(found, blb_source, tazobactam_intermediate_anchor, float(tazobactam_stock_volume_ul) + float(tazobactam_intermediate_blb_volume_ul), mix_volume_ul, mix_cycles, speed)

    _rl(f"▶ Preparing {len(working_solutions)} compound/control working solutions and one vehicle well")

    batched_dispense_mastermix(
        pipette=pipette,
        tipbox=tipbox,
        reagent_block=blb_source,
        reaction_plate=working_plate,
        mm_anchor=blb_anchor,
        wells=",".join(compound_dests),
        rxn_volume=compound_blb_volume_ul,
        num_reactions=len(compound_dests),
        speed=speed,
    )
    batched_dispense_mastermix(
        pipette=pipette,
        tipbox=tipbox,
        reagent_block=blb_source,
        reaction_plate=working_plate,
        mm_anchor=blb_anchor_2,
        wells=vehicle_dest_well,
        rxn_volume=vehicle_blb_volume_ul,
        num_reactions=1,
        speed=speed,
    )

    for label, source_plate, source_well, dest_well in working_solutions:
        if label == "Compound 1":
            _transfer_one(found, blb_source, tazobactam_intermediate_anchor, working_plate, dest_well, float(stock_volume_ul), "Compound 1 T1262 intermediate", speed)
        else:
            _transfer_one(found, source_plate, source_well, working_plate, dest_well, float(stock_volume_ul), label, speed)
    _transfer_one(found, dmso_source, dmso_anchor, working_plate, vehicle_dest_well, float(vehicle_dmso_volume_ul), "Vehicle DMSO", speed)

    for _, _, _, dest_well in working_solutions:
        _mix_well(found, working_plate, dest_well, float(compound_blb_volume_ul) + float(stock_volume_ul), mix_volume_ul, mix_cycles, speed)
    _mix_well(found, working_plate, vehicle_dest_well, float(vehicle_blb_volume_ul) + float(vehicle_dmso_volume_ul), mix_volume_ul, mix_cycles, speed)

    _rl("✓ Dilution plate complete: TEM-1 working solution is 0.1 ng/uL; T1262 well is 10 uM; other compound/control wells are 500 uM; vehicle well is 5% DMSO")
    return {"success": True, "tem1_working_anchor": tem1_working_anchor, "working_solutions": len(working_solutions), "vehicle_wells": 1}
