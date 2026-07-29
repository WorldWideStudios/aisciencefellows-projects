from protocol_schema import SkillObject

from execution.execution_functions import (
    clear_skill_variable,
    detach_object_from_arm,
    get_skill_variable,
    is_sim_mode,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
)
from utils import RIGHT_FORWARD_DOWN


ARM = "right_arm"
TRANSFER_STATE_KEY = "move_wellplate_to_openshelf.transfer"
ORIENTATION_DOT_MIN = 0.99999


def _quaternion_alignment(first, second):
    if len(first) != 4 or len(second) != 4:
        raise ValueError("Anchor quaternions must contain four values")
    first_norm = sum(value * value for value in first) ** 0.5
    second_norm = sum(value * value for value in second) ** 0.5
    if first_norm <= 0 or second_norm <= 0:
        raise ValueError("Anchor quaternions must be non-zero")
    return abs(
        sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm)
    )


def place_wellplate_in_openshelf(
    plate: SkillObject,
    openshelf: SkillObject,
    carry_grasp_anchor: str = "right_side_grasp_flipped",
    plate_place_anchor: str = "nest_base",
    shelf_anchor: str = "wellplate_slot_1",
    shelf_transit_tcp_anchor: str = (
        "wellplate_slot_1_right_side_flipped_transit_tcp"
    ),
    shelf_pre_tcp_anchor: str = "wellplate_slot_1_right_side_flipped_high_tcp",
    shelf_entry_tcp_anchor: str = "wellplate_slot_1_right_side_flipped_entry_tcp",
    shelf_tcp_anchor: str = "wellplate_slot_1_right_side_flipped_tcp",
    speed: float = 30.0,
    slow_speed: float = 10.0,
):
    """Insert a right-arm-held PCR wellplate horizontally into OpenShelf.

    The skill retains the horizontal side grasp from pickup through release.
    Every carry TCP anchor has the same orientation, so the plate stays level
    while the collision-aware planner checks the attached plate, OpenShelf, and
    tables at each move. The entry and release poses translate the plate through
    the front of the shelf without placing the gripper above it.

    Args:
        plate: PCR wellplate attached to the right arm by the pickup skill.
        openshelf: OpenShelf object providing transit and destination anchors.
        carry_grasp_anchor: Horizontal side grasp retained through release.
        plate_place_anchor: Plate frame aligned with the OpenShelf seat.
        shelf_anchor: OpenShelf seat where the plate is left after release.
        shelf_transit_tcp_anchor: Level free-space waypoint after pickup.
        shelf_pre_tcp_anchor: High collision-clear pose before shelf entry.
        shelf_entry_tcp_anchor: Side-grip pose immediately in front of the shelf.
        shelf_tcp_anchor: Side-grip release pose paired with the carry grasp.
        speed: Relative speed for free-space arm moves.
        slow_speed: Relative speed for insertion, release, and retreat.
    """
    anchor_names = {
        "carry_grasp_anchor": carry_grasp_anchor.strip(),
        "plate_place_anchor": plate_place_anchor.strip(),
        "shelf_anchor": shelf_anchor.strip(),
        "shelf_transit_tcp_anchor": shelf_transit_tcp_anchor.strip(),
        "shelf_pre_tcp_anchor": shelf_pre_tcp_anchor.strip(),
        "shelf_entry_tcp_anchor": shelf_entry_tcp_anchor.strip(),
        "shelf_tcp_anchor": shelf_tcp_anchor.strip(),
    }
    for parameter, anchor_name in anchor_names.items():
        if not anchor_name:
            raise ValueError(f"{parameter} must name an object-model anchor")
    if speed <= 0 or slow_speed <= 0:
        raise ValueError("speed and slow_speed must be positive")

    carry_grasp_anchor = anchor_names["carry_grasp_anchor"]
    plate_place_anchor = anchor_names["plate_place_anchor"]
    shelf_anchor = anchor_names["shelf_anchor"]
    shelf_transit_tcp_anchor = anchor_names["shelf_transit_tcp_anchor"]
    shelf_pre_tcp_anchor = anchor_names["shelf_pre_tcp_anchor"]
    shelf_entry_tcp_anchor = anchor_names["shelf_entry_tcp_anchor"]
    shelf_tcp_anchor = anchor_names["shelf_tcp_anchor"]

    transfer = get_skill_variable(TRANSFER_STATE_KEY)
    if not isinstance(transfer, dict):
        raise RuntimeError(
            "No wellplate transfer state was found; run "
            "pickup_wellplate_from_holder first in the same workflow"
        )
    if transfer.get("plate_id") != plate.id:
        raise RuntimeError("The requested plate does not match the attached plate")
    if transfer.get("arm") != ARM:
        raise RuntimeError("The transfer state does not leave the plate on the right arm")
    if transfer.get("pickup_grasp_anchor") != carry_grasp_anchor:
        raise RuntimeError("The carry grasp must match the grasp retained from pickup")
    if transfer.get("plate_level") is not True:
        raise RuntimeError("The pickup skill did not assert the level-plate contract")
    if transfer.get("plate_orientation_preserved") is not True:
        raise RuntimeError("The pickup skill did not preserve the plate orientation")
    if transfer.get("collision_planning_required") is not True:
        raise RuntimeError("The pickup skill did not assert collision-aware transport")

    grasp_width = transfer.get("grasp_width_m")
    if not isinstance(grasp_width, (int, float)) or grasp_width <= 0:
        raise RuntimeError("The pickup skill did not record a valid grasp width")
    carry_wxyz = transfer.get("carry_wxyz")
    if not isinstance(carry_wxyz, (list, tuple)) or len(carry_wxyz) != 4:
        raise RuntimeError("The pickup skill did not record the carried orientation")

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting place_wellplate_in_openshelf "
        f"(mode={'simulation' if is_sim_mode() else 'hardware'}, "
        f"arm={ARM}, seat={shelf_anchor}, plate_level=True, "
        "orientation_preserved=True, collision_planning=True)"
    )

    seat = load_object_anchor(openshelf.id, shelf_anchor)
    transit = load_object_anchor(openshelf.id, shelf_transit_tcp_anchor)
    pre_release = load_object_anchor(openshelf.id, shelf_pre_tcp_anchor)
    entry = load_object_anchor(openshelf.id, shelf_entry_tcp_anchor)
    release = load_object_anchor(openshelf.id, shelf_tcp_anchor)
    plate_place = load_object_anchor(plate.id, plate_place_anchor)
    if release["width"] <= grasp_width:
        raise ValueError(
            f"shelf TCP anchor {shelf_tcp_anchor!r} must open wider than "
            f"the recorded grasp width ({grasp_width} m)"
        )

    route = {
        shelf_transit_tcp_anchor: transit,
        shelf_pre_tcp_anchor: pre_release,
        shelf_entry_tcp_anchor: entry,
        shelf_tcp_anchor: release,
    }
    route_alignments = {}
    for anchor_name, target in route.items():
        alignment = _quaternion_alignment(carry_wxyz, target["wxyz"])
        route_alignments[anchor_name] = alignment
        if alignment < ORIENTATION_DOT_MIN:
            raise ValueError(
                f"OpenShelf TCP anchor {anchor_name!r} would rotate the plate "
                f"(quaternion alignment={alignment:.8f})"
            )

    seat_alignment = _quaternion_alignment(plate_place["wxyz"], seat["wxyz"])
    if seat_alignment < ORIENTATION_DOT_MIN:
        raise ValueError(
            f"OpenShelf seat {shelf_anchor!r} would change the plate orientation "
            f"(quaternion alignment={seat_alignment:.8f})"
        )

    print_log("Carrying the level plate through the right-arm transit pose")
    move_arm(
        arm=ARM,
        position=transit["xyz"],
        orientation=transit["rpy"],
        speed=speed,
        wait=True,
    )

    print_log("Moving the level plate to the high OpenShelf approach")
    move_arm(
        arm=ARM,
        position=pre_release["xyz"],
        orientation=pre_release["rpy"],
        speed=speed,
        wait=True,
    )

    print_log(
        "Inserting the level plate horizontally with collision-aware "
        "Cartesian moves"
    )
    move_arm(
        arm=ARM,
        position=entry["xyz"],
        orientation=entry["rpy"],
        speed=slow_speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=release["xyz"],
        orientation=release["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log("Releasing and seating the plate in OpenShelf")
    set_gripper(arm=ARM, width_m=release["width"])
    detach_object_from_arm(plate.id)
    snap_object_anchor_to_world_pose(
        plate.id,
        plate_place_anchor,
        seat["xyz"],
        seat["wxyz"],
    )
    clear_skill_variable(TRANSFER_STATE_KEY)

    print_log("Retreating the right arm through the collision-clear entry path")
    for target, target_speed in (
        (entry, slow_speed),
        (pre_release, slow_speed),
        (transit, speed),
    ):
        move_arm(
            arm=ARM,
            position=target["xyz"],
            orientation=target["rpy"],
            speed=target_speed,
            wait=True,
        )
    move_arm_js(arm=ARM, joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    print_log("place_wellplate_in_openshelf completed")
    return {
        "success": True,
        "arm": ARM,
        "carry_grasp_anchor": carry_grasp_anchor,
        "plate_place_anchor": plate_place_anchor,
        "shelf_anchor": shelf_anchor,
        "shelf_transit_tcp_anchor": shelf_transit_tcp_anchor,
        "shelf_pre_tcp_anchor": shelf_pre_tcp_anchor,
        "shelf_entry_tcp_anchor": shelf_entry_tcp_anchor,
        "shelf_tcp_anchor": shelf_tcp_anchor,
        "seat_xyz": seat["xyz"],
        "seat_wxyz": seat["wxyz"],
        "route_orientation_alignments": route_alignments,
        "seat_orientation_alignment": seat_alignment,
        "plate_level": True,
        "plate_orientation_preserved": True,
        "collision_planning": True,
    }
