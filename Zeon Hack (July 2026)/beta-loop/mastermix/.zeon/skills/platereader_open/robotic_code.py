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

# Lid articulation from plate_reader.object_model.yaml (lid_joint, radians):
#   closed -> 0.0, fully open -> 2.0386 (the "open" preset / URDF upper limit).
LID_CLOSED_ANGLE = 0.0
LID_OPEN_ANGLE = 1.83

ARM = "right_arm"
ARC_STEPS = 14              # joint-sweep waypoints (higher = smoother arc)
APPROACH_JAW_M = 0.06       # gripper opening for the approach (before pinching the lid)
APPROACH_SPEED = 80.0
DESCEND_SPEED = 40.0
SWING_SPEED = 40.0

# Right-arm clearance pose (shared with the shaker/thermo skills).
RIGHT_ARM_OUTER_SWING_JOINTS = [-2.145, -0.450, -0.957, -0.036, 1.380, 1.041]
RIGHT_ARM_OUTER_SWING_JOINTS_SAFE = [-1.158, -0.687, -1.131, -0.037, 1.809, 3.545]

def _sweep_lid(reader_id, anchor, start_angle, end_angle, steps, speed):
    """Arc-follow: drive lid_joint from ``start_angle`` to ``end_angle`` in ``steps``.

    At each step resolve ``anchor`` at that joint angle and move the arm to it, then
    commit the joint config, so the lid animates along its true hinge arc with the
    arm tracking it. ``anchor`` lives on the ``lid`` link, so it swings with the lid.
    """
    for i in range(1, steps + 1):
        t = i / steps
        angle = (1.0 - t) * start_angle + t * end_angle
        pose = load_object_anchor(reader_id, anchor, joint_config={"lid_joint": angle})
        move_arm(arm=ARM, position=pose["xyz"], orientation=pose["rpy"], speed=speed, wait=True)
        update_object_joint_config(reader_id, {"lid_joint": angle})


def platereader_open(platereader: SkillObject):
    """Open the plate reader lid by arc-following the ``lid_open`` anchor.

    Starts with the lid closed. Grips the lid at ``lid_open`` (resolved with the lid
    closed), then sweeps lid_joint from closed (0.0) to fully open (2.0386),
    resolving ``lid_open`` at each step so the lid traces its real hinge arc with the
    arm tracking it, committing the joint state as it goes. Releases and swings out.
    Single-anchor version of wellplate_shaker_open.

    Args:
        platereader: The plate reader whose lid to open.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting platereader_open")

    reader_id = platereader.id

    # Model the lid closed so the grab lands on the closed lid.
    update_object_joint_config(reader_id, {"lid_joint": LID_CLOSED_ANGLE})

    # Resolve the grab pose with the lid closed; pinch to the anchor's grasp width.
    lid = load_object_anchor(reader_id, "lid_open", joint_config={"lid_joint": LID_CLOSED_ANGLE})
    # lid_prepose = load_object_anchor(reader_id, "lid_open_body")
    grip_w = lid.get("width", 0.0)
    preapproach = anchor_preapproach(lid, standoff=0.05)
    preapproach_above = [preapproach[0], preapproach[1], preapproach[2] + 0.15]

    # Swing in, approach with the gripper open, and pinch the lid.
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_STOW_JOINTS)
    set_gripper(arm=ARM, width_m=APPROACH_JAW_M)
    move_arm(arm=ARM, position=preapproach_above, orientation=lid["rpy"], speed=APPROACH_SPEED, wait=True)
    move_arm(arm=ARM, position=preapproach, orientation=lid["rpy"], speed=APPROACH_SPEED, wait=True)
    move_arm(arm=ARM, position=lid["xyz"], orientation=lid["rpy"], speed=DESCEND_SPEED, wait=True)
    set_gripper(arm=ARM, width_m=grip_w)
    time.sleep(0.3)

    # Arc-follow lid_open from closed (0.0) to fully open (2.0386).
    _sweep_lid(reader_id, "lid_open", LID_CLOSED_ANGLE, LID_OPEN_ANGLE, ARC_STEPS, SWING_SPEED)

    retreat = load_object_anchor(reader_id, "lid_open_retreat")
    set_gripper(arm=ARM, width_m=0.02)
    time.sleep(0.3)
    move_arm(arm=ARM, position=retreat["xyz"], orientation=retreat["rpy"], speed=APPROACH_SPEED, wait=True)

    update_object_joint_config(reader_id, {"lid_joint": 2.0386})

    # Release the lid and swing out.
    set_gripper(arm=ARM, width_m=APPROACH_JAW_M)
    time.sleep(0.3)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_STOW_JOINTS)

    print_log("platereader_open completed")
    return {"success": True}
