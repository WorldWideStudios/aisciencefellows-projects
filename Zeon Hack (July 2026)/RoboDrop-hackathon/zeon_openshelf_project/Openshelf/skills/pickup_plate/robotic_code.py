import time

from protocol_schema import SkillObject

from execution.execution_functions import (
    anchor_preapproach,
    attach_object_to_arm,
    is_sim_mode,
    load_object_anchor,
    move_arm,
    move_arm_js,
    move_relative,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
)
from utils import RIGHT_FORWARD_FRONT


ARM = "right_arm"
GRASP_ANCHOR = "horizontal_grip"
OPEN_GRIPPER_WIDTH_M = 0.08
LIFT_CLEARANCE_M = 0.08
TRANSITION_SPEED = 0.5
APPROACH_SPEED = 30.0
SLOW_SPEED = 10.0
OPEN_SETTLE_S = 0.1
GRASP_SETTLE_S = 0.5
CLOSE_SETTLE_S = 0.1


def pickup_plate(target: SkillObject):
    """Pick up a PCR plate using its horizontal right-arm grasp anchor.

    The right arm starts from its named horizontal transition pose, approaches
    directly through the ``horizontal_grip`` standoff with the final wrist
    orientation, asserts a canonical grip in the world model, attaches the
    plate, and lifts without changing its orientation.

    Args:
        target: PCR plate world object to pick up.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting pickup_plate "
        f"(mode={'simulation' if is_sim_mode() else 'hardware'}, "
        f"arm={ARM}, grasp_anchor={GRASP_ANCHOR})"
    )

    grasp = load_object_anchor(target.id, GRASP_ANCHOR)
    grasp_width = grasp["width"]
    grasp_standoff = grasp["standoff"]
    if not isinstance(grasp_width, (int, float)) or grasp_width <= 0:
        raise ValueError(
            f"plate anchor {GRASP_ANCHOR!r} needs a positive grasp width"
        )
    if not isinstance(grasp_standoff, (int, float)) or grasp_standoff <= 0:
        raise ValueError(
            f"plate anchor {GRASP_ANCHOR!r} needs a positive standoff"
        )

    pre_grasp = anchor_preapproach(grasp)
    print_log(
        "Resolved horizontal pickup poses "
        f"(pre_grasp={pre_grasp}, grasp={grasp['xyz']}, "
        f"standoff_m={grasp_standoff}, width_m={grasp_width})"
    )

    print_log("Stage transition: moving right arm to RIGHT_FORWARD_FRONT")
    try:
        move_arm_js(
            arm=ARM,
            joint_angles=RIGHT_FORWARD_FRONT,
            speed=TRANSITION_SPEED,
        )
    except Exception as exc:
        raise RuntimeError(
            f"pickup_plate failed during transition: {exc}"
        ) from exc
    print_log("Stage transition: complete")

    print_log("Stage open: opening the right gripper")
    try:
        set_gripper(arm=ARM, width_m=OPEN_GRIPPER_WIDTH_M)
        time.sleep(OPEN_SETTLE_S)
    except Exception as exc:
        raise RuntimeError(
            f"pickup_plate failed while opening the gripper: {exc}"
        ) from exc
    print_log("Stage open: complete")

    print_log("Stage pre_grasp: moving to horizontal_grip standoff")
    try:
        move_arm(
            arm=ARM,
            position=pre_grasp,
            orientation=grasp["rpy"],
            speed=APPROACH_SPEED,
            wait=True,
        )
    except Exception as exc:
        raise RuntimeError(
            f"pickup_plate failed while moving to pre_grasp: {exc}"
        ) from exc
    print_log("Stage pre_grasp: complete")

    print_log("Stage grasp: advancing horizontally to the plate")
    try:
        move_arm(
            arm=ARM,
            position=grasp["xyz"],
            orientation=grasp["rpy"],
            speed=SLOW_SPEED,
            wait=True,
        )
        time.sleep(GRASP_SETTLE_S)
    except Exception as exc:
        raise RuntimeError(
            f"pickup_plate failed during final grasp approach: {exc}"
        ) from exc
    print_log("Stage grasp: complete")

    print_log("Closing the gripper and asserting the canonical plate grip")
    try:
        set_gripper(arm=ARM, width_m=grasp_width)
        time.sleep(CLOSE_SETTLE_S)
        snap_object_anchor_to_world_pose(
            target.id,
            GRASP_ANCHOR,
            grasp["xyz"],
            grasp["wxyz"],
        )
        attach_object_to_arm(target.id, arm=ARM)
    except Exception as exc:
        raise RuntimeError(
            f"pickup_plate failed while closing and attaching: {exc}"
        ) from exc
    print_log("Stage attach: complete")

    print_log("Stage lift: lifting the plate without changing orientation")
    try:
        move_relative(
            arm=ARM,
            delta_xyz=[0.0, 0.0, LIFT_CLEARANCE_M],
            speed=SLOW_SPEED,
            wait=True,
        )
    except Exception as exc:
        raise RuntimeError(f"pickup_plate failed during lift: {exc}") from exc
    print_log("Stage lift: complete")

    print_log("pickup_plate completed")
    return {
        "success": True,
        "arm": ARM,
        "grasp_anchor": GRASP_ANCHOR,
        "grasp_width_m": grasp_width,
        "grasp_standoff_m": grasp_standoff,
        "lift_m": LIFT_CLEARANCE_M,
        "plate_orientation_preserved": True,
        "collision_planning_required": True,
    }
