from protocol_schema import SkillObject
from utils import attach_next_tip, ensure_pipette, find_pipettes, pipette_name

from batched_dispense_mastermix.robotic_code import batched_dispense_mastermix
from epipette_aspirate.robotic_code import epipette_aspirate
from epipette_dispense.robotic_code import epipette_dispense
from epipette_eject.robotic_code import epipette_eject

from .modules import print_log


def _rl(msg, kind="event"):
    print_log(msg, runlog=True, runlog_type=kind)


def _obj_id(obj):
    return getattr(obj, "id", str(obj))


def _transfer_one(found, src_obj, src_anchor, dst_obj, dst_anchor, volume, label, speed):
    pipette, tipbox = found.get("epipette_10ul") or next(iter(found.values()))
    ensure_pipette(pipette, found)
    tip = attach_next_tip(pipette, tipbox)
    _rl(f"  {label}: {volume} uL source {_obj_id(src_obj)} / {src_anchor} -> working {_obj_id(dst_obj)} / {dst_anchor} ({pipette_name(pipette)}, tip #{tip})", "transfer")
    epipette_aspirate(object=src_obj, anchor=src_anchor, pipette=pipette, volume=volume, speed=speed)
    epipette_dispense(object=dst_obj, anchor=dst_anchor, pipette=pipette, volume=volume, speed=speed)
    epipette_eject(pipette=pipette)


def _mix_well(found, plate, well, contents_volume, mix_volume, cycles, speed):
    pipette, tipbox = found.get("epipette_10ul") or next(iter(found.values()))
    ensure_pipette(pipette, found)
    tip = attach_next_tip(pipette, tipbox)
    mv = min(float(mix_volume), max(0.5, float(contents_volume) - 1.0), 10.0)
    _rl(f"  Mix working {well}: {cycles} cycles x {mv} uL ({pipette_name(pipette)}, tip #{tip})", "mix")
    for _ in range(max(1, int(cycles))):
        epipette_aspirate(object=plate, anchor=well, pipette=pipette, volume=mv, speed=speed)
        epipette_dispense(object=plate, anchor=well, pipette=pipette, volume=mv, speed=speed)
    epipette_eject(pipette=pipette)


def _validate_working_solutions(working_solutions):
    missing = [label for label, _, source_well, dest_well in working_solutions if not str(source_well).strip() or not str(dest_well).strip()]
    if missing:
        raise ValueError(
            "Missing source or working destination wells for: " + ", ".join(missing)
        )
    sources = [(label, _obj_id(source_plate), str(source_well).strip().upper()) for label, source_plate, source_well, _ in working_solutions]
    duplicate_sources = sorted({f"{source_plate}/{source_well}" for _, source_plate, source_well in sources if sum(1 for _, sp, sw in sources if sp == source_plate and sw == source_well) > 1})
    if duplicate_sources:
        raise ValueError("Duplicate source stock locations: " + ", ".join(duplicate_sources))
    dests = [str(dest_well).strip().upper() for _, _, _, dest_well in working_solutions]
    duplicates = sorted({dest for dest in dests if dests.count(dest) > 1})
    if duplicates:
        raise ValueError("Duplicate working-plate destination wells: " + ", ".join(duplicates))


def prepare_tem1_manual_stock_working_plate(
    pipette: SkillObject,
    tipbox: SkillObject,
    blb_source: SkillObject,
    dmso_source: SkillObject,
    working_plate: SkillObject,
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
    vehicle_blb_anchor: str = "hole_6",
    dmso_anchor: str = "hole_9",
    positive_source_well: str = "H7",
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
    mix_volume_ul: float = 10.0,
    mix_cycles: int = 5,
    speed: float = 5.0,
):
    """Prepare positive/control/compound working solutions from source stocks.

    The operator provides the large/source stocks. The robot builds a working
    plate with 50 uL positive/test-compound working solutions and one 100 uL
    matched vehicle well. All eight R3 v1 test compounds use the same transfer
    logic; no compound receives special intermediate dilution handling.
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
    _validate_working_solutions(working_solutions)
    working_dests = [dest for _, _, _, dest in working_solutions]

    _rl(f"Preparing {len(working_solutions)} positive/test-compound working solutions plus matched vehicle")
    for label, source_plate, source_well, dest_well in working_solutions:
        _rl(f"  Stock-source mapping: {label} source {_obj_id(source_plate)} / {source_well} -> working {_obj_id(working_plate)} / {dest_well}", "source_map")

    batched_dispense_mastermix(
        pipette=pipette,
        tipbox=tipbox,
        reagent_block=blb_source,
        reaction_plate=working_plate,
        mm_anchor=blb_anchor,
        wells=",".join(working_dests),
        rxn_volume=compound_blb_volume_ul,
        num_reactions=len(working_dests),
        speed=speed,
    )
    batched_dispense_mastermix(
        pipette=pipette,
        tipbox=tipbox,
        reagent_block=blb_source,
        reaction_plate=working_plate,
        mm_anchor=vehicle_blb_anchor,
        wells=vehicle_dest_well,
        rxn_volume=vehicle_blb_volume_ul,
        num_reactions=1,
        speed=speed,
    )

    for label, source_plate, source_well, dest_well in working_solutions:
        _transfer_one(found, source_plate, source_well, working_plate, dest_well, float(stock_volume_ul), label, speed)
    _transfer_one(found, dmso_source, dmso_anchor, working_plate, vehicle_dest_well, float(vehicle_dmso_volume_ul), "Vehicle DMSO", speed)

    for _, _, _, dest_well in working_solutions:
        _mix_well(found, working_plate, dest_well, float(compound_blb_volume_ul) + float(stock_volume_ul), mix_volume_ul, mix_cycles, speed)
    _mix_well(found, working_plate, vehicle_dest_well, float(vehicle_blb_volume_ul) + float(vehicle_dmso_volume_ul), mix_volume_ul, mix_cycles, speed)

    _rl("Manual-stock working plate complete: positive/test compounds are 500 uM; vehicle is 5% DMSO")
    return {"success": True, "working_solutions": len(working_solutions), "vehicle_wells": 1}
