import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS, snap_plate_into_gripper

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    update_object_joint_config,
)

# Shaker lid-open angle for the revolute lid_joint ("open" preset; closed is 0.0).
LID_OPEN_ANGLE = 1.6721

# Right-arm swing pose that clears the deck on the way in and out of the shaker.
RIGHT_ARM_OUTER_SWING_JOINTS_180 = [-2.145, -0.450, -0.957, -0.036, 1.380, 4.183]
RIGHT_ARM_OUTER_SWING_JOINTS_SAFE = [-1.158, -0.687, -1.131, -0.037, 1.809, 3.545]

def wellplate_shaker_unload(object: SkillObject, wellplate_shaker: SkillObject, slot_anchor: str = "slot_1"):
    """Pick a plate out of a shaker slot with the right arm.

    Grabs at ``<slot_anchor>_unload`` — the settled pose ~4 mm below the slot that
    ``wellplate_shaker_load`` leaves the plate at. After closing it asserts the
    canonical grip via ``snap_plate_into_gripper`` (snaps the plate's grasp_shortside
    onto the gripper and attaches), so the plate is held identically to every other
    pick regardless of where its tracked pose was. Works for any slot: slot_1..slot_4.

    Args:
        object: The well plate sitting in the shaker slot, to pick back out.
        wellplate_shaker: The shaker to unload from.
        slot_anchor: Slot to pick from (slot_1..slot_4); grabs at its ``_unload`` twin.
    """
    print_log(runlog=True, runlog_type="step_start")
    shaker_id = wellplate_shaker.id
    plate_id = object.id
    unload_anchor = f"{slot_anchor}_unload"
    print_log(f"Starting wellplate_shaker_unload: plate {plate_id} <- {unload_anchor}")

    update_object_joint_config(shaker_id, {"lid_joint": LID_OPEN_ANGLE})

    unload = load_object_anchor(shaker_id, unload_anchor)
    preapproach = anchor_preapproach(unload, standoff=0.15)

    # Swing in with an open gripper.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_180, speed=0.8)
    set_gripper(arm="right_arm", width_m=0.10)

    # Approach and descend to the settled grab pose.
    move_arm(arm="right_arm", position=preapproach, orientation=unload["rpy"], speed=60)
    move_arm(arm="right_arm", position=unload["xyz"], orientation=unload["rpy"], speed=30)

    # Close, then assert the canonical grip: snap grasp_shortside onto the gripper
    # (wherever it actually is) and attach — the same grip every pick uses.
    set_gripper(arm="right_arm", width_m=0.085)
    time.sleep(0.5)
    set_gripper(arm="right_arm", width_m=0.08)  
    time.sleep(0.5)
    set_gripper(arm="right_arm", width_m=0.075)
    snap_plate_into_gripper(plate_id)

    # Lift out through the preapproach, then stow.
    move_arm(arm="right_arm", position=preapproach, orientation=unload["rpy"], speed=50)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_180)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)


    print_log("wellplate_shaker_unload completed")
    return {"success": True}
