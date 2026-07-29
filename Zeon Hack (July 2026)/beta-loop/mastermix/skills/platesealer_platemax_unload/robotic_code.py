import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS, snap_plate_into_gripper

from .modules import (
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
)

# Skill-local right-arm swing pose that clears the deck on the way into and out
# of the sealer. Calibrated for this cell; kept from the original routine, not
# derived from any object model.
RIGHT_ARM_INNER_SWING_JOINT_180 = [1.675, -0.730, -0.815, 0.043, 1.567, 1.691]


def platesealer_platemax_unload(
    object: SkillObject,
    platesealer: SkillObject,
    preapproach_1_anchor: str = "plate_preapproach_1",
    preapproach_2_anchor: str = "plate_preapproach_2",
    unload_anchor: str = "plate_unload",
    open_width_m: float = 0.10,
    grip_width_m: float = 0.065,
    approach_speed: float = 60,
    load_speed: float = 30,
    retreat_speed: float = 50,
):
    """Pick a plate back out of a plate sealer, driven entirely by anchors.

    The inverse of platesealer_platemax_load. The sealer's object model defines the
    path as anchors: ``plate_preapproach_1`` (lined up in front of the drawer),
    ``plate_preapproach_2`` (directly above the load position), and ``plate_unload``
    (3 mm underneath plate_load, so the fingers close under the seated plate). The
    right arm swings in with an open gripper, moves along preapproach_1 ->
    preapproach_2, descends onto plate_unload, closes, then asserts the canonical grip
    (snaps grasp_shortside onto the gripper + attaches) so the plate is held
    identically to every other pick, then retreats back out along preapproach_2 ->
    preapproach_1 and stows. Nothing about the sealer geometry is baked into this file
    — re-teach the anchors and the motion follows.

    Args:
        object: The well plate sitting in the sealer, to pick back out.
        platesealer: The plate sealer to unload from.
        preapproach_1_anchor: First (outermost) approach anchor on the sealer.
        preapproach_2_anchor: Second approach anchor, directly above the load anchor.
        unload_anchor: Grab pose the gripper descends onto and grips — 3 mm underneath
            plate_load so the fingers close under the seated plate.
        open_width_m: Gripper width to open to for the approach, wide enough to clear
            the plate as the arm descends onto it.
        grip_width_m: Final gripper width that clamps the plate before attaching.
        approach_speed: Speed for the two preapproach moves.
        load_speed: Speed for the final descent onto the load anchor.
        retreat_speed: Speed for the retreat moves carrying the plate back out.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting platesealer_platemax_unload")

    sealer_id = platesealer.id
    plate_id = object.id

    # Resolve the extraction path from the sealer's object model. The grab pose is
    # plate_unload — 3 mm underneath plate_load — so the fingers close under the
    # seated plate.
    preapproach_1 = load_object_anchor(sealer_id, preapproach_1_anchor)
    preapproach_2 = load_object_anchor(sealer_id, preapproach_2_anchor)
    unload = load_object_anchor(sealer_id, unload_anchor)

    # Swing in over the deck with an open gripper so the fingers clear the plate.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180, speed=0.8)
    set_gripper(arm="right_arm", width_m=open_width_m)

    # Approach open: preapproach_1 -> preapproach_2 -> descend onto the plate.
    move_arm(arm="right_arm", position=preapproach_1["xyz"], orientation=preapproach_1["rpy"], speed=approach_speed)
    move_arm(arm="right_arm", position=preapproach_2["xyz"], orientation=preapproach_2["rpy"], speed=approach_speed)
    move_arm(arm="right_arm", position=unload["xyz"], orientation=unload["rpy"], speed=load_speed)
    time.sleep(0.5)

    # Close on the plate, then assert the canonical grip: snap grasp_shortside onto
    # the gripper (wherever it actually is) and attach — the same grip every pick uses.
    set_gripper(arm="right_arm", width_m=grip_width_m)
    time.sleep(0.5)
    snap_plate_into_gripper(plate_id)

    # Retreat back out along the same anchors in reverse with the plate in hand, then stow.
    move_arm(arm="right_arm", position=preapproach_2["xyz"], orientation=preapproach_2["rpy"], speed=retreat_speed)
    move_arm(arm="right_arm", position=preapproach_1["xyz"], orientation=preapproach_1["rpy"], speed=retreat_speed)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)

    print_log("platesealer_platemax_unload completed")
    return {"success": True}
