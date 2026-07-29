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


def move_wellplate_to_openshelf_physical(
    plate: SkillObject,
    openshelf: SkillObject,
    shelf_anchor: str = "wellplate_slot_1",
    holder_clear_tcp_anchor: str = "wellplate_slot_1_holder_clear_tcp",
    pickup_exit_tcp_anchor: str = "wellplate_slot_1_pickup_exit_tcp",
    shelf_transit_tcp_anchor: str = "wellplate_slot_1_transit_tcp",
    shelf_pre_tcp_anchor: str = "wellplate_slot_1_pre_tcp",
    shelf_tcp_anchor: str = "wellplate_slot_1_tcp",
    plate_grasp_anchor: str = "grasp_short_clearance_flipped",
    plate_place_anchor: str = "nest_base",
    arm: str = "left_arm",
    lift_m: float = 0.08,
    speed: float = 30.0,
    slow_speed: float = 10.0,
):
    """Pick a PCR plate and place it into a named OpenShelf seat.

    The plate is normalized to its anchor-defined grip before attachment, then
    carried to the shelf. At release, its seating anchor is snapped to the
    OpenShelf seat so the world model matches the commanded physical placement.

    Args:
        plate: PCR wellplate object to pick up.
        openshelf: OpenShelf object that provides the destination anchors.
        shelf_anchor: Seat anchor where the plate is left after release.
        holder_clear_tcp_anchor: Short lateral waypoint that clears the holder.
        pickup_exit_tcp_anchor: Waypoint that clears the source holder.
        shelf_transit_tcp_anchor: High waypoint between pickup and shelf entry.
        shelf_pre_tcp_anchor: Collision-clear pose before entering the shelf.
        shelf_tcp_anchor: TCP release anchor paired with the plate grasp.
        plate_grasp_anchor: TCP-convention anchor used to grasp the plate.
        plate_place_anchor: Plate anchor aligned to the shelf seat on release.
        arm: Arm used for the complete pick-and-place operation.
        lift_m: World-Z lift after grasping, in metres.
        speed: Relative speed for free-space moves.
        slow_speed: Relative speed for grasp, lift, release, and retreat.
    """
    shelf_anchor = shelf_anchor.strip()
    holder_clear_tcp_anchor = holder_clear_tcp_anchor.strip()
    pickup_exit_tcp_anchor = pickup_exit_tcp_anchor.strip()
    shelf_transit_tcp_anchor = shelf_transit_tcp_anchor.strip()
    shelf_pre_tcp_anchor = shelf_pre_tcp_anchor.strip()
    shelf_tcp_anchor = shelf_tcp_anchor.strip()
    plate_grasp_anchor = plate_grasp_anchor.strip()
    plate_place_anchor = plate_place_anchor.strip()
    arm = arm.strip()

    anchor_names = {
        "shelf_anchor": shelf_anchor,
        "holder_clear_tcp_anchor": holder_clear_tcp_anchor,
        "pickup_exit_tcp_anchor": pickup_exit_tcp_anchor,
        "shelf_transit_tcp_anchor": shelf_transit_tcp_anchor,
        "shelf_pre_tcp_anchor": shelf_pre_tcp_anchor,
        "shelf_tcp_anchor": shelf_tcp_anchor,
        "plate_grasp_anchor": plate_grasp_anchor,
        "plate_place_anchor": plate_place_anchor,
    }
    for parameter, anchor_name in anchor_names.items():
        if not anchor_name:
            raise ValueError(f"{parameter} must name an object-model anchor")
    if arm not in {"left_arm", "right_arm"}:
        raise ValueError("arm must be 'left_arm' or 'right_arm'")
    if not 0.02 <= lift_m <= 0.20:
        raise ValueError("lift_m must be between 0.02 and 0.20 metres")
    if speed <= 0 or slow_speed <= 0:
        raise ValueError("speed and slow_speed must be positive")

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting move_wellplate_to_openshelf_physical "
        f"(mode={'simulation' if is_sim_mode() else 'hardware'}, arm={arm}, "
        f"grasp={plate_grasp_anchor}, seat={shelf_anchor})"
    )

    grasp = load_object_anchor(plate.id, plate_grasp_anchor)
    load_object_anchor(plate.id, plate_place_anchor)
    seat = load_object_anchor(openshelf.id, shelf_anchor)
    holder_clear = load_object_anchor(openshelf.id, holder_clear_tcp_anchor)
    pickup_exit = load_object_anchor(openshelf.id, pickup_exit_tcp_anchor)
    transit = load_object_anchor(openshelf.id, shelf_transit_tcp_anchor)
    pre_release = load_object_anchor(openshelf.id, shelf_pre_tcp_anchor)
    release = load_object_anchor(openshelf.id, shelf_tcp_anchor)

    if grasp["width"] <= 0:
        raise ValueError(
            f"plate anchor {plate_grasp_anchor!r} needs a positive grasp width"
        )
    if release["width"] <= grasp["width"]:
        raise ValueError(
            f"shelf TCP anchor {shelf_tcp_anchor!r} must open wider than "
            f"plate grasp anchor {plate_grasp_anchor!r}"
        )

    pre_grasp = anchor_preapproach(grasp)
    print_log("Opening the gripper and approaching the plate")
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

    print_log("Closing the gripper and lifting the plate clear of its source fixture")
    set_gripper(arm=arm, width_m=grasp["width"])
    move_relative(
        arm=arm,
        delta_xyz=[0.0, 0.0, lift_m],
        speed=slow_speed,
        wait=True,
    )

    print_log("Moving the plate slowly through the source-clear waypoints")
    lifted_grasp_xyz = [
        grasp["xyz"][0],
        grasp["xyz"][1],
        grasp["xyz"][2] + lift_m,
    ]
    holder_clear_delta = [
        holder_clear["xyz"][axis] - lifted_grasp_xyz[axis]
        for axis in range(3)
    ]
    for _ in range(3):
        move_relative(
            arm=arm,
            delta_xyz=[delta / 3.0 for delta in holder_clear_delta],
            speed=slow_speed,
            wait=True,
        )
    move_arm(
        arm=arm,
        position=pickup_exit["xyz"],
        orientation=pickup_exit["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log("Synchronizing the cleared plate pose and attaching its world model")
    snap_object_anchor_to_world_pose(
        plate.id,
        plate_grasp_anchor,
        pickup_exit["xyz"],
        pickup_exit["wxyz"],
    )
    attach_object_to_arm(plate.id, arm)

    print_log("Carrying the attached plate through the transit waypoint")
    move_arm(
        arm=arm,
        position=transit["xyz"],
        orientation=transit["rpy"],
        speed=speed,
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

    print_log("Releasing and seating the plate")
    set_gripper(arm=arm, width_m=release["width"])
    detach_object_from_arm(plate.id)
    snap_object_anchor_to_world_pose(
        plate.id,
        plate_place_anchor,
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

    print_log("move_wellplate_to_openshelf_physical completed")
    return {
        "success": True,
        "arm": arm,
        "plate_grasp_anchor": plate_grasp_anchor,
        "plate_place_anchor": plate_place_anchor,
        "shelf_anchor": shelf_anchor,
        "holder_clear_tcp_anchor": holder_clear_tcp_anchor,
        "pickup_exit_tcp_anchor": pickup_exit_tcp_anchor,
        "shelf_transit_tcp_anchor": shelf_transit_tcp_anchor,
        "shelf_pre_tcp_anchor": shelf_pre_tcp_anchor,
        "shelf_tcp_anchor": shelf_tcp_anchor,
        "seat_xyz": seat["xyz"],
        "seat_wxyz": seat["wxyz"],
    }
