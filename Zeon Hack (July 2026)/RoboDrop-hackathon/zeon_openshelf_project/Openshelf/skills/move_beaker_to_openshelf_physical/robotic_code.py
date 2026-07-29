from protocol_schema import SkillObject

from execution.execution_functions import (
    anchor_preapproach,
    attach_object_to_arm,
    detach_object_from_arm,
    is_sim_mode,
    load_object_anchor,
    move_arm,
    move_relative,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
)


def move_beaker_to_openshelf_physical(
    beaker: SkillObject,
    openshelf: SkillObject,
    shelf_anchor: str = "beaker_slot_1",
    shelf_pre_tcp_anchor: str = "beaker_slot_1_pre_tcp",
    shelf_tcp_anchor: str = "beaker_slot_1_tcp",
    beaker_grasp_anchor: str = "side_grasp_left",
    beaker_place_anchor: str = "object",
    arm: str = "left_arm",
    lift_m: float = 0.10,
    speed: float = 40.0,
    slow_speed: float = 10.0,
):
    """Pick a beaker and place it into a named OpenShelf seat.

    The skill uses a beaker grasp anchor for pickup, a matching OpenShelf TCP
    anchor for the release motion, and a seat anchor for the final world-model
    snap. It commands arm and gripper motion in both simulation and hardware
    execution modes.

    Args:
        beaker: Beaker object to pick up.
        openshelf: OpenShelf object that provides the destination anchors.
        shelf_anchor: Seat anchor where the beaker is left after release.
        shelf_pre_tcp_anchor: Taught free-space pose before the shelf target.
        shelf_tcp_anchor: TCP release anchor paired with the shelf seat.
        beaker_grasp_anchor: TCP-convention anchor used to grasp the beaker.
        beaker_place_anchor: Beaker anchor aligned to the shelf seat on release.
        arm: Arm used for the complete pick-and-place operation.
        lift_m: World-Z lift after grasping, in metres.
        speed: Relative speed for free-space moves.
        slow_speed: Relative speed for final grasp and release moves.
    """
    shelf_anchor = shelf_anchor.strip()
    shelf_pre_tcp_anchor = shelf_pre_tcp_anchor.strip()
    shelf_tcp_anchor = shelf_tcp_anchor.strip()
    beaker_grasp_anchor = beaker_grasp_anchor.strip()
    beaker_place_anchor = beaker_place_anchor.strip()
    arm = arm.strip()

    anchor_names = {
        "shelf_anchor": shelf_anchor,
        "shelf_pre_tcp_anchor": shelf_pre_tcp_anchor,
        "shelf_tcp_anchor": shelf_tcp_anchor,
        "beaker_grasp_anchor": beaker_grasp_anchor,
        "beaker_place_anchor": beaker_place_anchor,
    }
    for parameter, anchor_name in anchor_names.items():
        if not anchor_name:
            raise ValueError(f"{parameter} must name an object-model anchor")
    if arm not in {"left_arm", "right_arm"}:
        raise ValueError("arm must be 'left_arm' or 'right_arm'")
    if not 0.02 <= lift_m <= 0.30:
        raise ValueError("lift_m must be between 0.02 and 0.30 metres")
    if speed <= 0 or slow_speed <= 0:
        raise ValueError("speed and slow_speed must be positive")

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting move_beaker_to_openshelf_physical "
        f"(mode={'simulation' if is_sim_mode() else 'hardware'}, arm={arm}, "
        f"grasp={beaker_grasp_anchor}, seat={shelf_anchor})"
    )

    grasp = load_object_anchor(beaker.id, beaker_grasp_anchor)
    seat = load_object_anchor(openshelf.id, shelf_anchor)
    pre_release = load_object_anchor(openshelf.id, shelf_pre_tcp_anchor)
    release = load_object_anchor(openshelf.id, shelf_tcp_anchor)

    if grasp["width"] <= 0:
        raise ValueError(
            f"beaker anchor {beaker_grasp_anchor!r} needs a positive grasp width"
        )
    if release["width"] <= grasp["width"]:
        raise ValueError(
            f"shelf TCP anchor {shelf_tcp_anchor!r} must open wider than "
            f"beaker grasp anchor {beaker_grasp_anchor!r}"
        )

    pre_grasp = anchor_preapproach(grasp)

    print_log("Opening gripper and approaching the beaker")
    set_gripper(arm=arm, width_m=release["width"])
    move_arm(
        arm=arm,
        position=pre_grasp,
        orientation=grasp["rpy"],
        speed=speed,
        wait=True,
    )
    move_arm(
        arm=arm,
        position=grasp["xyz"],
        orientation=grasp["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log("Closing gripper and attaching the beaker to the arm")
    set_gripper(arm=arm, width_m=grasp["width"])
    snap_object_anchor_to_world_pose(
        beaker.id,
        beaker_grasp_anchor,
        grasp["xyz"],
        grasp["wxyz"],
    )
    attach_object_to_arm(beaker.id, arm)
    move_relative(
        arm=arm,
        delta_xyz=[0.0, 0.0, lift_m],
        speed=slow_speed,
        wait=True,
    )

    print_log("Approaching the OpenShelf release pose")
    move_arm(
        arm=arm,
        position=pre_release["xyz"],
        orientation=pre_release["rpy"],
        speed=speed,
        wait=True,
    )
    move_arm(
        arm=arm,
        position=release["xyz"],
        orientation=release["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log("Releasing and seating the beaker")
    set_gripper(arm=arm, width_m=release["width"])
    detach_object_from_arm(beaker.id)
    snap_object_anchor_to_world_pose(
        beaker.id,
        beaker_place_anchor,
        seat["xyz"],
        seat["wxyz"],
    )

    move_arm(
        arm=arm,
        position=pre_release["xyz"],
        orientation=pre_release["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log("move_beaker_to_openshelf_physical completed")
    return {
        "success": True,
        "arm": arm,
        "beaker_grasp_anchor": beaker_grasp_anchor,
        "beaker_place_anchor": beaker_place_anchor,
        "shelf_anchor": shelf_anchor,
        "shelf_pre_tcp_anchor": shelf_pre_tcp_anchor,
        "shelf_tcp_anchor": shelf_tcp_anchor,
        "seat_xyz": seat["xyz"],
        "seat_wxyz": seat["wxyz"],
    }
