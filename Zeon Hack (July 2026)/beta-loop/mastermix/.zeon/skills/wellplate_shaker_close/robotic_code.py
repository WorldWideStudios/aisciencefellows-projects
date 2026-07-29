import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    update_object_joint_config,
)

# Lid articulation from wellplate_shaker.object_model.yaml (lid_joint, radians):
#   closed -> 0.0, open -> LID_OPEN_ANGLE (matches wellplate_shaker_open's final state).
LID_CLOSED_ANGLE = 0.3
LID_OPEN_ANGLE = 1.65
LID_MID_ANGLE = 1.15         # switch from lid_close to lid_close_2 at this angle

ARM = "right_arm"
OPEN_WIDTH_M = 0.08         # keep the gripper open and ride the lid down — lid_close's own
                            # grasp.width is 0.0 (push semantics), which we deliberately ignore.
ARC_STEPS = 12              # joint-sweep waypoints (higher = smoother arc)
APPROACH_SPEED = 80.0
DESCEND_SPEED = 30.0
SWING_SPEED = 25.0

# Skill-local right-arm clearance pose (shared with thermo_eppendorf_load).
RIGHT_ARM_OUTER_SWING_JOINTS = [-2.145, -0.450, -0.957, -0.036, 1.380, 1.041]
RIGHT_ARM_OUTER_SWING_JOINTS_SAFE = [-1.158, -0.687, -1.131, -0.037, 1.809, 3.545]


def _sweep_lid(shaker_id, anchor, start_angle, end_angle, steps, speed):
    """Arc-follow: drive lid_joint from start_angle to end_angle in ``steps``, and at
    each step resolve ``anchor`` at that joint angle and move the arm to it, so the
    lid animates along its true articulation arc with the arm tracking it."""
    for i in range(1, steps + 1):
        t = i / steps
        angle = (1.0 - t) * start_angle + t * end_angle
        pose = load_object_anchor(shaker_id, anchor, joint_config={"lid_joint": angle})
        move_arm(arm=ARM, position=pose["xyz"], orientation=pose["rpy"], speed=speed, wait=True)
        update_object_joint_config(shaker_id, {"lid_joint": angle})


def wellplate_shaker_close(shaker: SkillObject):
    """Close the wellplate shaker lid by arc-following the ``lid_close`` anchor down.

    Mirror of wellplate_shaker_open's arc mechanism, but single-anchor: it uses only
    ``lid_close`` and never grips — the gripper stays open and rides the lid down.

    Starts with the lid open. Approaches ``lid_close`` (resolved with the lid open)
    with the gripper open, then closes in two arc-following stages:
      - Stage 1: arc-follows ``lid_close`` from the open config down to
        ``LID_MID_ANGLE`` (0.6).
      - Reposition: moves to ``lid_close_2`` at the mid config.
      - Stage 2: arc-follows ``lid_close_2`` from ``LID_MID_ANGLE`` down to closed
        (0.0).
    Each step resolves the anchor at the interpolated lid_joint angle, moves the arm
    there, and commits that angle, so the lid traces its real articulation arc down.

    Args:
        shaker: The wellplate shaker whose lid to close.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting wellplate_shaker_close")

    shaker_id = shaker.id

    # Model the lid open so the approach lands on the open lid.
    update_object_joint_config(shaker_id, {"lid_joint": LID_OPEN_ANGLE})

    # Resolve the contact pose with the lid open.
    lid = load_object_anchor(shaker_id, "lid_close", joint_config={"lid_joint": LID_OPEN_ANGLE})
    preapproach = anchor_preapproach(lid, standoff=0.05)

    # Swing in and approach with the gripper open (ride the lid, do not grip).
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS)
    set_gripper(arm=ARM, width_m=OPEN_WIDTH_M)
    move_arm(arm=ARM, position=preapproach, orientation=lid["rpy"], speed=APPROACH_SPEED, wait=True)
    move_arm(arm=ARM, position=lid["xyz"], orientation=lid["rpy"], speed=DESCEND_SPEED, wait=True)
    time.sleep(0.3)

    set_gripper(arm=ARM, width_m=0.02)
    # Stage 1: arc-follow lid_close down, open (LID_OPEN_ANGLE) -> mid (0.6).
    _sweep_lid(shaker_id, "lid_close", LID_OPEN_ANGLE, LID_MID_ANGLE, ARC_STEPS, SWING_SPEED)
    set_gripper(arm=ARM, width_m=0.08)

    # Reposition to lid_close_2 at the mid config; it takes the lid the rest of the way.
    lid2 = load_object_anchor(shaker_id, "lid_close_2", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid2["xyz"], orientation=lid2["rpy"], speed=DESCEND_SPEED, wait=True)
    
    # Stage 2: arc-follow lid_close_2 down, mid (0.6) -> closed (0.0).
    _sweep_lid(shaker_id, "lid_close_2", LID_MID_ANGLE, LID_CLOSED_ANGLE, ARC_STEPS, SWING_SPEED)

    # Back off to the preapproach of lid_close_2 (lid now closed) before swinging out.
    lid2_closed = load_object_anchor(shaker_id, "lid_close_2", joint_config={"lid_joint": LID_CLOSED_ANGLE})
    lid2_pre = anchor_preapproach(lid2_closed, standoff=0.05)
    move_arm(arm=ARM, position=lid2_pre, orientation=lid2_closed["rpy"], speed=APPROACH_SPEED, wait=True)

    update_object_joint_config(shaker_id, {"lid_joint": 0.0})

    # Swing out.
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_STOW_JOINTS, speed=0.8)

    print_log("wellplate_shaker_close completed")
    return {"success": True}
