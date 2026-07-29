import time

from execution.skill_editing import shared_state
from utils import LEFT_ARM_STOW_JOINTS, PRE_PICK_JOINTS

from .modules import (
    attach_object_to_arm,
    get_object_pose,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    set_skill_variable,
)

# Skill-local right-arm pose (post-pick tip-check stance); intentionally
# distinct from the shared RIGHT_ARM_STOW_JOINTS in utils.
_RIGHT_ARM_STOW_JOINTS = [-0.210, -0.680, -0.864, -0.026, 1.607, 4.496]

ABOVE_OFFSET_Z = 0.13


def epipette_grey_pick():
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting epipette_grey_pick")

    try:
        pose = get_object_pose("epipette_grey")
        shared_state.epipette_home_pose = {
            "object_id": pose["object_id"],
            "xyz": pose["xyz"],
            "wxyz": pose["wxyz"],
        }
    except ValueError:
        pose = None

    grasp = load_object_anchor("epipette_grey", "grasp_pose")
    pick_xyz = grasp["xyz"]
    pick_ori = grasp["rpy"]
    set_skill_variable("epipette_grey_pick_pose", {"xyz": pick_xyz, "ori": pick_ori})

    move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_STOW_JOINTS, speed=0.5)
    move_arm_js(arm="right_arm", joint_angles=_RIGHT_ARM_STOW_JOINTS, speed=0.5)
    move_arm_js(arm="left_arm", joint_angles=PRE_PICK_JOINTS, speed=0.5)

    move_arm(
        arm="left_arm",
        position=[pick_xyz[0], pick_xyz[1], pick_xyz[2] + ABOVE_OFFSET_Z],
        orientation=pick_ori,
        speed=50,
        wait=True,
    )
    set_gripper(arm="left_arm", width_m=0.05)
    time.sleep(0.1)

    move_arm(
        arm="left_arm",
        position=[pick_xyz[0], pick_xyz[1], pick_xyz[2]],
        orientation=pick_ori,
        speed=30,
        wait=True,
    )
    time.sleep(0.5)
    set_gripper(arm="left_arm", width_m=0.035)
    time.sleep(0.1)
    set_gripper(arm="left_arm", width_m=0.012)
    time.sleep(0.2)

    if pose:
        try:
            attach_object_to_arm(pose["object_id"], arm="left_arm")
        except ValueError:
            pass

    move_arm(
        arm="left_arm",
        position=[pick_xyz[0], pick_xyz[1], pick_xyz[2] + ABOVE_OFFSET_Z],
        orientation=pick_ori,
        speed=150,
        wait=True,
    )

    move_arm_js(arm="right_arm", joint_angles=_RIGHT_ARM_STOW_JOINTS, speed=0.5)

    print_log("epipette_grey_pick completed")
    return {"success": True}
