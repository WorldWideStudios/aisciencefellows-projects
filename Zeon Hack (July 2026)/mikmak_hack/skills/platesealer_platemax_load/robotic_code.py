import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS

from .modules import (
    detach_object_from_arm,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
    update_object_joint_config,
)

# Drawer-open angle for the platesealer's prismatic drawer_joint — the
# geometry_open preset in the object model (closed is 0.0).
DRAWER_OPEN_ANGLE = 0.131

# Skill-local right-arm swing pose that clears the deck on the way into and out
# of the sealer. Calibrated for this cell; kept from the original routine, not
# derived from any object model.
RIGHT_ARM_INNER_SWING_JOINT_180 = [1.675, -0.730, -0.815, 0.043, 1.567, 1.691]


def platesealer_platemax_load(
    object: SkillObject,
    platesealer: SkillObject,
    preapproach_1_anchor: str = "plate_preapproach_1",
    preapproach_2_anchor: str = "plate_preapproach_2",
    load_anchor: str = "plate_load",
    unload_anchor: str = "plate_unload",
    release_width_m: float = 0.10,
    approach_speed: float = 60,
    load_speed: float = 5,
    retreat_speed: float = 20,
):
    """Load a plate into a plate sealer and release it, driven entirely by anchors.

    The sealer's object model defines the whole insertion path as three anchors:
    ``plate_preapproach_1`` (lined up in front of the drawer), ``plate_preapproach_2``
    (directly above the load position), and ``plate_load`` (the seated load pose).
    The right arm carries the held plate along preapproach_1 -> preapproach_2 ->
    load, detaches and opens the gripper to release the plate there, snaps the plate
    onto ``plate_unload`` (3 mm below plate_load, where it settles — the exact pose
    platesealer_platemax_unload grabs from), then retreats back out along
    preapproach_2 -> preapproach_1 and stows. Nothing about the sealer geometry is
    baked into this file — re-teach the anchors and the motion follows.

    Args:
        object: The well plate currently held by the right arm, to load into the sealer.
        platesealer: The plate sealer to load into.
        preapproach_1_anchor: First (outermost) approach anchor on the sealer.
        preapproach_2_anchor: Second approach anchor, directly above the load anchor.
        load_anchor: Seated load position where the plate is released.
        unload_anchor: Settled pose (3 mm below plate_load) the plate is snapped onto
            after release, so it sits exactly where the unload skill grabs it.
        release_width_m: Gripper width to open to when releasing the plate.
        approach_speed: Speed for the two preapproach moves carrying the plate in.
        load_speed: Speed for the final descent onto the load anchor.
        retreat_speed: Speed for the retreat moves back out of the sealer.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting platesealer_platemax_load")

    sealer_id = platesealer.id
    plate_id = object.id

    # Model the sealer drawer as open for the whole load (drawer_joint = 0.131,
    # the geometry_open preset) so the world reflects the open drawer we load into.
    update_object_joint_config(sealer_id, {"drawer_joint": DRAWER_OPEN_ANGLE})

    # Resolve the insertion path from the sealer's object model.
    preapproach_1 = load_object_anchor(sealer_id, preapproach_1_anchor)
    preapproach_2 = load_object_anchor(sealer_id, preapproach_2_anchor)
    load = load_object_anchor(sealer_id, load_anchor)
    unload = load_object_anchor(sealer_id, unload_anchor)

    # Swing in over the deck with the plate in hand.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180, speed=0.8)

    # Carry the plate in: preapproach_1 -> preapproach_2 -> load.
    move_arm(arm="right_arm", position=preapproach_1["xyz"], orientation=preapproach_1["rpy"], speed=approach_speed)
    move_arm(arm="right_arm", position=preapproach_2["xyz"], orientation=preapproach_2["rpy"], speed=approach_speed)
    move_arm(arm="right_arm", position=load["xyz"], orientation=load["rpy"], speed=load_speed)
    time.sleep(0.5)

    # Release the plate at the load pose: detach from the arm, then open the gripper.
    detach_object_from_arm(plate_id)
    set_gripper(arm="right_arm", width_m=release_width_m)
    time.sleep(0.5)

    # Seat the plate at plate_unload (3 mm below plate_load, where it settles) so sim
    # places it exactly where platesealer_platemax_unload picks it up.
    snap_object_anchor_to_world_pose(plate_id, "grasp_shortside", unload["xyz"], unload["wxyz"])

    # Retreat back out along the same anchors in reverse, then stow.
    move_arm(arm="right_arm", position=preapproach_2["xyz"], orientation=preapproach_2["rpy"], speed=retreat_speed)
    move_arm(arm="right_arm", position=preapproach_1["xyz"], orientation=preapproach_1["rpy"], speed=retreat_speed)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)

    print_log("platesealer_platemax_load completed")
    return {"success": True}
