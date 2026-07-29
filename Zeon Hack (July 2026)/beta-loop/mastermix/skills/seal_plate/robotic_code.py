"""Super-skill: seal a well plate on the PlateMax, then return it home.

Generic (no ``cfps_`` prefix) — composes the wellplate + platesealer atomics into
one grab -> seal -> drop closure so any workflow can seal a plate in a single node.
Sequence: grab the plate short-side, open the sealer door, load the plate, peel and
place a seal, close the door, press the seal button, unload the sealed plate, and
drop it back onto its home anchor.

Progress is emitted to the run log at every stage via ``print_log(..., runlog=True)``.
"""

from protocol_schema import SkillObject

from platesealer_pick_seal.robotic_code import platesealer_pick_seal
from platesealer_platemax_door.robotic_code import platesealer_platemax_door
from platesealer_platemax_load.robotic_code import platesealer_platemax_load
from platesealer_platemax_place_seal.robotic_code import platesealer_platemax_place_seal
from platesealer_platemax_seal.robotic_code import platesealer_platemax_seal
from platesealer_platemax_unload.robotic_code import platesealer_platemax_unload
from wellplate_drop.robotic_code import wellplate_drop
from wellplate_grab.robotic_code import wellplate_grab

from .modules import print_log


def _rl(msg, kind="event"):
    """Emit a run-log line (shown in the run log panel)."""
    print_log(msg, runlog=True, runlog_type=kind)


def seal_plate(
    plate: SkillObject,
    platesealer: SkillObject,
    seal_holder: SkillObject,
    home_destination: SkillObject,
    home_anchor: str = "home",
    grasp_anchor: str = "grasp_shortside",
    seal_index: int = 1,
):
    """Grab a plate, seal it on the PlateMax, and drop it back home.

    Args:
        plate: The well plate to seal (grabbed short-side, returned home).
        platesealer: The PlateMax sealer object.
        seal_holder: The stacked seal holder to peel a seal from.
        home_destination: Object whose ``home_anchor`` the plate is dropped onto.
        home_anchor: Destination anchor name on ``home_destination`` (default "home").
        grasp_anchor: Grasp anchor on the plate (default short-side).
        seal_index: 1-based seal position in the holder to pick.
    """
    print_log(runlog=True, runlog_type="step_start")

    _rl("seal_plate: grab plate (short-side)")
    wellplate_grab(object=plate, grasp_anchor=grasp_anchor)

    _rl("seal_plate: open sealer door")
    platesealer_platemax_door()

    _rl("seal_plate: load plate into sealer")
    platesealer_platemax_load(object=plate, platesealer=platesealer)

    _rl(f"seal_plate: pick seal #{seal_index}")
    platesealer_pick_seal(seal_holder_stacked=seal_holder, seal_index=seal_index)

    _rl("seal_plate: place seal on plate")
    platesealer_platemax_place_seal(platesealer=platesealer)

    _rl("seal_plate: close sealer door")
    platesealer_platemax_door()

    _rl("seal_plate: press seal button")
    platesealer_platemax_seal()

    _rl("seal_plate: unload sealed plate")
    platesealer_platemax_unload(object=plate, platesealer=platesealer)

    _rl(f"seal_plate: drop plate home ({home_anchor})")
    wellplate_drop(
        object=plate,
        destination=home_destination,
        destination_anchor=home_anchor,
        grasp_anchor=grasp_anchor,
    )

    print_log("seal_plate completed")
    return {"success": True}
