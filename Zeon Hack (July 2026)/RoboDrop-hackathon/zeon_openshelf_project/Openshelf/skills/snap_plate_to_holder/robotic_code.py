from protocol_schema import SkillObject

from .modules import (
    load_object_anchor,
    print_log,
    snap_object_anchor_to_world_pose,
)


def snap_plate_to_holder(
    plate: SkillObject,
    holder: SkillObject,
    plate_anchor: str = "bottom_center",
    holder_anchor: str = "plate_slot",
):
    """Snap a plate anchor onto a holder seat anchor.

    Args:
        plate: Plate object to move.
        holder: Holder object that provides the seat anchor.
        plate_anchor: Anchor on the plate that should land on the holder seat.
        holder_anchor: Seat anchor on the holder.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting snap_plate_to_holder "
        f"(plate_anchor={plate_anchor}, holder_anchor={holder_anchor})"
    )

    seat = load_object_anchor(holder.id, holder_anchor)
    placed = load_object_anchor(plate.id, plate_anchor)

    print_log(
        "snap_plate_to_holder: "
        f"holder {holder.id}.{holder_anchor} xyz={seat['xyz']} wxyz={seat['wxyz']}"
    )
    print_log(
        "snap_plate_to_holder: "
        f"plate {plate.id}.{plate_anchor} current xyz={placed['xyz']} wxyz={placed['wxyz']}"
    )

    snap_object_anchor_to_world_pose(
        plate.id,
        plate_anchor,
        seat["xyz"],
        seat["wxyz"],
    )

    print_log("snap_plate_to_holder completed")
    return {
        "success": True,
        "plate_anchor": plate_anchor,
        "holder_anchor": holder_anchor,
        "target_xyz": seat["xyz"],
        "target_wxyz": seat["wxyz"],
    }
