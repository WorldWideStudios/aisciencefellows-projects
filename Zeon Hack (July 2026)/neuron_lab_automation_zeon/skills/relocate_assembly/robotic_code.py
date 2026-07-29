import time

from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN, object_display_name

from .modules import (
    attach_object_to_arm,
    detach_object_from_arm,
    get_object_pose,
    load_object_anchor,
    move_arm,
    move_arm_js,
    move_relative,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
    snap_object_to_world_pose,
)

OPEN_CLEARANCE_M = 0.02


def relocate_assembly(
    base: SkillObject,
    passenger: SkillObject,
    dx: float = 0.0,
    dy: float = -0.10,
    dz: float = 0.0,
    grasp_anchor: str = "grasp",
    seat_anchor: str = "round_holder_seat",
    passenger_anchor: str = "bottom_center",
    arm: str = "left_arm",
    lift_clear_m: float = 0.05,
):
    """Grip `base`, move both scene objects together, and set them down.

    The passenger is snapped onto the base's seat before pickup. Both objects
    are attached to the active arm during transit, then detached and re-snapped
    after placement so the simulator keeps them aligned.
    """
    stow = {"left_arm": LEFT_FORWARD_DOWN, "right_arm": RIGHT_FORWARD_DOWN}

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        f"Starting relocate_assembly "
        f"(base={base.id}, passenger={passenger.id}, delta=({dx}, {dy}, {dz}))"
    )

    base_home = get_object_pose(object_display_name(base))

    seat = load_object_anchor(base.id, seat_anchor)
    snap_object_anchor_to_world_pose(
        passenger.id,
        passenger_anchor,
        seat["xyz"],
        seat["wxyz"],
    )

    move_arm_js(arm="left_arm", joint_angles=LEFT_FORWARD_DOWN, speed=0.5)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    grasp = load_object_anchor(base.id, grasp_anchor)

    set_gripper(arm=arm, width_m=grasp["width"] + OPEN_CLEARANCE_M)
    time.sleep(0.1)
    move_arm(arm=arm, position=grasp["xyz"], orientation=grasp["rpy"], speed=30, wait=True)
    time.sleep(0.3)
    set_gripper(arm=arm, width_m=grasp["width"])
    time.sleep(0.2)

    # The base is physically gripped. Mounting the seated passenger to the same
    # TCP makes both scene objects follow the carry motion together.
    attach_object_to_arm(base.id, arm)
    attach_object_to_arm(passenger.id, arm)

    move_relative(arm=arm, delta_xyz=[0.0, 0.0, lift_clear_m])
    move_relative(arm=arm, delta_xyz=[dx, dy, dz])
    move_relative(arm=arm, delta_xyz=[0.0, 0.0, -lift_clear_m])
    time.sleep(0.3)

    set_gripper(arm=arm, width_m=grasp["width"] + OPEN_CLEARANCE_M)
    time.sleep(0.2)
    detach_object_from_arm(passenger.id)
    detach_object_from_arm(base.id)

    snap_object_to_world_pose(
        base_home["object_id"],
        [base_home["xyz"][0] + dx, base_home["xyz"][1] + dy, base_home["xyz"][2] + dz],
        base_home["wxyz"],
    )

    moved_seat = load_object_anchor(base.id, seat_anchor)
    snap_object_anchor_to_world_pose(
        passenger.id,
        passenger_anchor,
        moved_seat["xyz"],
        moved_seat["wxyz"],
    )

    move_arm_js(arm=arm, joint_angles=stow[arm], speed=0.5)

    print_log("relocate_assembly completed; passenger re-seated on moved base")
    return {
        "success": True,
        "assembly_attached_during_transit": True,
        "seat_anchor": seat_anchor,
        "passenger_anchor": passenger_anchor,
    }
