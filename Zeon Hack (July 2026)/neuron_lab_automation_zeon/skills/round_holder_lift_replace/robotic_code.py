from execution.execution_functions import (
    SkillObject,
    anchor_preapproach,
    attach_object_to_arm,
    detach_object_from_arm,
    load_object_anchor,
    move_arm,
    move_arm_js,
    move_relative,
    pause_aware_sleep,
    print_log,
    set_gripper,
    set_world_state,
    snap_object_anchor_to_world_pose,
)
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN


TRANSIT_SPEED = 60
GRIPPER_OPEN_CLEARANCE_M = 0.02


def round_holder_lift_replace(
    round_holder: SkillObject,
    holder: SkillObject,
    arm: str = "right_arm",
    grasp_anchor: str = "grasp_shortside",
    seat_anchor: str = "round_holder_seat",
    placement_anchor: str = "bottom_center",
    lift_height_m: float = 0.05,
    hold_seconds: float = 1.0,
    speed: float = 20,
):
    """Lift the round holder vertically off its seat, pause, and replace it.

    The skill returns the tool centre point to the exact grasp pose captured
    before the lift. After release, it pins ``placement_anchor`` to the holder's
    ``seat_anchor`` so the world model matches the calibrated seated pose.

    Args:
        round_holder: Round mock-plate object initially seated on the holder.
        holder: Receiving wellplate holder carrying the calibrated seat anchor.
        arm: Arm to use; must be ``left_arm`` or ``right_arm``.
        grasp_anchor: TCP-convention grasp anchor on the round holder.
        seat_anchor: Destination seat anchor on the receiving holder.
        placement_anchor: Placement frame on the round holder aligned to the seat.
        lift_height_m: Vertical world-frame lift distance in metres.
        hold_seconds: Pause duration while the part is visibly off the holder.
        speed: Relative speed for grasp, lift, descent, and retreat moves.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting round_holder_lift_replace "
        f"(arm={arm}, grasp={grasp_anchor}, seat={seat_anchor}, "
        f"lift={lift_height_m}m)"
    )

    if arm not in {"left_arm", "right_arm"}:
        raise ValueError("arm must be 'left_arm' or 'right_arm'")
    if not 0.01 <= lift_height_m <= 0.15:
        raise ValueError("lift_height_m must be between 0.01 and 0.15 metres")
    if not 0.0 <= hold_seconds <= 10.0:
        raise ValueError("hold_seconds must be between 0 and 10 seconds")
    if speed <= 0:
        raise ValueError("speed must be positive")

    # Clear both arms to the standard forward/down transition poses before
    # approaching the centre deck. Move the inactive arm first.
    if arm == "right_arm":
        move_arm_js("left_arm", LEFT_FORWARD_DOWN, speed=0.5)
        move_arm_js("right_arm", RIGHT_FORWARD_DOWN, speed=0.5)
        active_stow = RIGHT_FORWARD_DOWN
    else:
        move_arm_js("right_arm", RIGHT_FORWARD_DOWN, speed=0.5)
        move_arm_js("left_arm", LEFT_FORWARD_DOWN, speed=0.5)
        active_stow = LEFT_FORWARD_DOWN

    grasp = load_object_anchor(round_holder.id, grasp_anchor)
    if grasp["width"] <= 0:
        raise ValueError(
            f"anchor {grasp_anchor!r} must define a positive grasp width"
        )

    pregrasp = anchor_preapproach(grasp)
    open_width = grasp["width"] + GRIPPER_OPEN_CLEARANCE_M

    set_gripper(arm, open_width)
    move_arm(
        arm=arm,
        position=pregrasp,
        orientation=grasp["rpy"],
        speed=TRANSIT_SPEED,
        wait=True,
    )
    move_arm(
        arm=arm,
        position=grasp["xyz"],
        orientation=grasp["rpy"],
        speed=speed,
        wait=True,
    )
    set_gripper(arm, grasp["width"])

    # Canonicalize the simulated/world-model grip before attaching the object.
    snap_object_anchor_to_world_pose(
        round_holder.id,
        grasp_anchor,
        grasp["xyz"],
        grasp["wxyz"],
    )
    attach_object_to_arm(round_holder.id, arm)

    move_relative(
        arm=arm,
        delta_xyz=[0.0, 0.0, lift_height_m],
        speed=speed,
        wait=True,
    )
    pause_aware_sleep(hold_seconds)

    # Returning to the captured grasp pose replaces the physical part exactly
    # where this run found it, without inventing an absolute TCP target.
    move_arm(
        arm=arm,
        position=grasp["xyz"],
        orientation=grasp["rpy"],
        speed=speed,
        wait=True,
    )
    set_gripper(arm, open_width)
    detach_object_from_arm(round_holder.id)

    # Assert the calibrated final relationship for planning and later skills.
    seat = load_object_anchor(holder.id, seat_anchor)
    snap_object_anchor_to_world_pose(
        round_holder.id,
        placement_anchor,
        seat["xyz"],
        seat["wxyz"],
    )
    set_world_state(holder.id, {"round_holder_state": "seated"})

    move_arm(
        arm=arm,
        position=pregrasp,
        orientation=grasp["rpy"],
        speed=speed,
        wait=True,
    )
    move_arm_js(arm, active_stow, speed=0.5)

    print_log("round_holder_lift_replace completed; round holder is seated")
    return {
        "success": True,
        "round_holder_state": "seated",
        "lift_height_m": lift_height_m,
    }
