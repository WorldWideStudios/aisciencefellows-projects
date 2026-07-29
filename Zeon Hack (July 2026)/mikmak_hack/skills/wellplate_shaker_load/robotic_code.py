import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS

from .modules import (
    anchor_preapproach,
    detach_object_from_arm,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
    update_object_joint_config,
)

# Shaker lid-open angle for the revolute lid_joint ("open" preset; closed is 0.0).
LID_OPEN_ANGLE = 1.6721

# Right-arm swing pose that clears the deck on the way in and out of the shaker.
RIGHT_ARM_OUTER_SWING_JOINTS_180 = [-2.145, -0.450, -0.957, -0.036, 1.380, 4.183]
RIGHT_ARM_PLATE_PICK = [0.797, -0.376, -1.065, 0.012, 1.472, 0.813]
RIGHT_ARM_OUTER_SWING_JOINTS_SAFE = [-1.158, -0.687, -1.131, -0.037, 1.809, 3.545]

def wellplate_shaker_load(object: SkillObject, wellplate_shaker: SkillObject, slot_anchor: str = "slot_1"):
    """Place a held plate into a shaker slot with the right arm and release it.

    Holds the plate at the slot grasp pose (``slot_anchor``) and opens the gripper,
    then snaps the plate to ``<slot_anchor>_unload`` — the settled spot ~4 mm lower
    that the plate drops to on release. That is exactly the pose
    ``wellplate_shaker_unload`` grabs from, so pick and drop can't disagree. Works
    for any slot: pass slot_1..slot_4.

    Args:
        object: The well plate held by the right arm, to place into the shaker.
        wellplate_shaker: The shaker to load into.
        slot_anchor: Slot to place into (slot_1..slot_4).
    """
    print_log(runlog=True, runlog_type="step_start")
    shaker_id = wellplate_shaker.id
    plate_id = object.id
    unload_anchor = f"{slot_anchor}_unload"
    print_log(f"Starting wellplate_shaker_load: plate {plate_id} -> {slot_anchor}")

    update_object_joint_config(shaker_id, {"lid_joint": LID_OPEN_ANGLE})

    slot = load_object_anchor(shaker_id, slot_anchor)
    unload = load_object_anchor(shaker_id, unload_anchor)
    preapproach = anchor_preapproach(slot, standoff=0.15)

    # Swing in with the plate in hand, then descend onto the slot grasp pose.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK, speed=0.8)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_180, speed=0.8)
    move_arm(arm="right_arm", position=preapproach, orientation=slot["rpy"], speed=60)
    move_arm(arm="right_arm", position=slot["xyz"], orientation=slot["rpy"], speed=30)
    time.sleep(0.5)

    # Release, then snap the plate to the settled (unload) pose it drops to — the
    # exact spot wellplate_shaker_unload picks it up from.
    detach_object_from_arm(plate_id)
    set_gripper(arm="right_arm", width_m=0.10)
    time.sleep(0.5)
    snap_object_anchor_to_world_pose(plate_id, "grasp_shortside", unload["xyz"], unload["wxyz"])

    # Retreat through the preapproach, then stow.
    move_arm(arm="right_arm", position=preapproach, orientation=slot["rpy"], speed=50)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_180)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_OUTER_SWING_JOINTS_SAFE)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)

    print_log("wellplate_shaker_load completed")
    return {"success": True}
