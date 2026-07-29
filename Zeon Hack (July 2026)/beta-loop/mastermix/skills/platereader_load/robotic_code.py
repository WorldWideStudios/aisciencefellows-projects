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

# Plate reader lid-open angle for the revolute lid_joint (closed is 0.0).
LID_OPEN_ANGLE = 2.0386

# Right-arm swing pose that clears the deck on the way in and out of the reader.
RIGHT_ARM_OUTER_SWING_JOINTS_180 = [-2.145, -0.450, -0.957, -0.036, 1.380, 4.183]
RIGHT_ARM_PLATE_PICK = [0.797, -0.376, -1.065, 0.012, 1.472, 0.813]

def platereader_load(
    object: SkillObject,
    platereader: SkillObject,
    load_anchor: str = "load_plate",
    unload_anchor: str = "unload_plate",
    plate_grasp_anchor: str = "grasp_longside_platereader",
):
    """Place a held plate into the plate reader load position and release it.

    Assumes the lid is already open (models lid_joint = open so the load pose is
    clear — run platereader_open first). Descends onto the ``load_anchor`` grasp pose
    with the right arm, releases, and snaps the plate onto ``unload_anchor`` — the
    settled pose where the plate sits, and the exact pose platereader_unload grabs
    from, so load and unload can't disagree. Mirror of wellplate_shaker_load.

    Args:
        object: The well plate held by the right arm, to place into the reader.
        platereader: The plate reader to load into.
        load_anchor: Anchor on the reader to descend onto (default 'load_plate').
        unload_anchor: Settled pose the plate is snapped onto after release, where
            platereader_unload picks it up (default 'unload_plate').
        plate_grasp_anchor: The plate's own grasp anchor to snap by (default
            'grasp_longside_platereader'; use the plate family's grasp anchor).
    """
    print_log(runlog=True, runlog_type="step_start")
    reader_id = platereader.id
    plate_id = object.id
    print_log(f"Starting platereader_load: plate {plate_id} -> {load_anchor}")

    # Model the lid open so the load pose is clear.
    update_object_joint_config(reader_id, {"lid_joint": LID_OPEN_ANGLE})

    load = load_object_anchor(reader_id, load_anchor)
    unload = load_object_anchor(reader_id, unload_anchor)
    preapproach = anchor_preapproach(load, standoff=0.1)

    # Swing in with the plate in hand, then descend onto the load grasp pose.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK, speed=0.8)
    move_arm(arm="right_arm", position=preapproach, orientation=load["rpy"], speed=60)
    move_arm(arm="right_arm", position=load["xyz"], orientation=load["rpy"], speed=30)
    time.sleep(0.5)

    # Release, then snap the plate to the load pose so the sim shows it seated.
    detach_object_from_arm(plate_id)
    set_gripper(arm="right_arm", width_m=0.10)
    time.sleep(0.5)
    snap_object_anchor_to_world_pose(plate_id, plate_grasp_anchor, load["xyz"], load["wxyz"])

    # Retreat through the preapproach, then stow.
    move_arm(arm="right_arm", position=preapproach, orientation=load["rpy"], speed=50)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK, speed=0.8)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)

    print_log("platereader_load completed")
    return {"success": True}
