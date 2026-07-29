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
#   closed -> 0.0, then opened in two stages via two grip anchors.
LID_CLOSED_ANGLE = 0.0
# LID_MID_ANGLE = 1.345       # end of stage 1 (lid_open) / start of stage 2 (lid_open_2)
LID_MID_ANGLE = 1.3
LID_OPEN_ANGLE = 1.65       # end of stage 2

ARM = "right_arm"
GRIP_WIDTH_M = 0.0          # pinch the lid at the grab point (tune in sim)
ARC_STEPS = 12              # joint-sweep waypoints per stage (higher = smoother arc)
APPROACH_SPEED = 80.0
DESCEND_SPEED = 50.0
SWING_SPEED = 50.0

# Skill-local right-arm clearance pose (shared with thermo_eppendorf_load).
RIGHT_ARM_OUTER_SWING_JOINTS_180 = [-2.145, -0.450, -0.957, -0.036, 1.380, 4.183]
RIGHT_ARM_OUTER_SWING_JOINTS = [-2.145, -0.450, -0.957, -0.036, 1.380, 1.041]
RIGHT_ARM_PLATE_PICK = [0.797, -0.376, -1.065, 0.012, 1.472, 0.813]
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


def wellplate_shaker_open(shaker: SkillObject):
    """Open the wellplate shaker lid in two arc-following stages.

    Starts with the lid closed. Approaches the ``lid_open`` anchor (resolved with the
    lid closed) with the gripper open and grips the lid, then:
      - Stage 1: sweeps lid_joint from closed (0.0) to ``LID_MID_ANGLE`` (1.345),
        following ``lid_open`` step-by-step so the lid traces its real arc.
      - Reposition: moves to ``lid_open_2`` (different wrist orientation) at the mid
        config.
      - Stage 2: moves in a straight line to ``lid_open_3`` (resolved at the open
        config) for the rest of the swing, committing lid_joint = ``LID_OPEN_ANGLE``
        (1.60).
    Stage 1 commits the lid_joint world state at each step (arc-following); stage 2
    commits it once at the end.

    Args:
        shaker: The wellplate shaker whose lid to open.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting wellplate_shaker_open")

    shaker_id = shaker.id

    # Model the lid closed so the grab lands on the closed lid.
    update_object_joint_config(shaker_id, {"lid_joint": LID_CLOSED_ANGLE})

    # Resolve the grab pose with the lid closed.
    lid = load_object_anchor(shaker_id, "lid_open", joint_config={"lid_joint": LID_CLOSED_ANGLE})
    jaw_open = lid.get("width", 0.08)
    preapproach = anchor_preapproach(lid, standoff=0.05)

    # Swing in, approach with the gripper open, and grip the lid.
    # move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS)
    set_gripper(arm=ARM, width_m=jaw_open)
    move_arm(arm=ARM, position=preapproach, orientation=lid["rpy"], speed=APPROACH_SPEED, wait=True)
    move_arm(arm=ARM, position=lid["xyz"], orientation=lid["rpy"], speed=DESCEND_SPEED, wait=True)
    set_gripper(arm=ARM, width_m=GRIP_WIDTH_M)
    time.sleep(0.3)

    # Stage 1: arc-follow lid_open, closed (0.0) -> mid (1.345).
    _sweep_lid(shaker_id, "lid_open", LID_CLOSED_ANGLE, LID_MID_ANGLE, ARC_STEPS, SWING_SPEED)

    # Reposition to lid_open_2 at the mid config (same grab point, new wrist orientation).
    lid2 = load_object_anchor(shaker_id, "lid_open_2", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid2["xyz"], orientation=lid2["rpy"], speed=DESCEND_SPEED, wait=True)

    # Stage 2: straight line to lid_open_3 (resolved at the open config) for the rest
    # of the swing, mid (1.345) -> open (1.60).
    lid3 = load_object_anchor(shaker_id, "lid_open_3", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid3["xyz"], orientation=lid3["rpy"], speed=SWING_SPEED, wait=True)
    lid4 = load_object_anchor(shaker_id, "lid_open_4", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid4["xyz"], orientation=lid4["rpy"], speed=DESCEND_SPEED, wait=True)
    lid5 = load_object_anchor(shaker_id, "lid_open_5", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid5["xyz"], orientation=lid5["rpy"], speed=SWING_SPEED, wait=True)
    
    time.sleep(0.3)

    lid4 = load_object_anchor(shaker_id, "lid_open_4", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid4["xyz"], orientation=lid4["rpy"], speed=DESCEND_SPEED, wait=True)
    lid3 = load_object_anchor(shaker_id, "lid_open_3", joint_config={"lid_joint": LID_MID_ANGLE})
    move_arm(arm=ARM, position=lid3["xyz"], orientation=lid3["rpy"], speed=SWING_SPEED, wait=True)

    update_object_joint_config(shaker_id, {"lid_joint": LID_OPEN_ANGLE})

    # Release the lid and swing out.
    set_gripper(arm=ARM, width_m=jaw_open)
    time.sleep(0.3)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_STOW_JOINTS, speed=0.8)

    print_log("wellplate_shaker_open completed")
    return {"success": True}
