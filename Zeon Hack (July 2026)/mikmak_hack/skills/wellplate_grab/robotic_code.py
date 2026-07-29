import time

from protocol_schema import SkillObject
from utils import snap_plate_into_gripper

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
)

# Skill-local right-arm poses that clear the deck before the descent onto the
# plate. Kept from wellplate_pcr_grab; calibrated for this cell, not derived from
# any object model.
RIGHT_ARM_INNER_SWING_JOINT_180 = [1.675, -0.730, -0.815, 0.043, 1.567, 1.691]
RIGHT_ARM_PLATE_PICK = [0.797, -0.376, -1.065, 0.012, 1.472, 0.813]


def wellplate_grab(
    object: SkillObject,
    grasp_anchor: str = "grasp_shortside",
    open_width_m: float = 0.10,
    approach_width_m: float = 0.085,
    grip_width_m: float = 0.075,
    lift_m: float = 0.05,
):
    """Pick up a plate with the right arm at a named grasp anchor.

    Anchor-driven: the approach standoff and a lift above it are computed from the
    grasp anchor via ``anchor_preapproach``. After closing on the plate it asserts
    the canonical grip via ``snap_plate_into_gripper`` — the plate's grasp anchor is
    snapped exactly onto the gripper and attached — so the plate is held identically
    on every pick and downstream drop/load never has to trust its tracked pose.

    Flow: swing in over the deck (two fixed clearance poses), open the gripper, move
    to a lifted standoff above the grasp anchor, down to the standoff, pre-open,
    descend onto the grasp pose, close, snap-into-gripper + attach, retract.

    Args:
        object: The plate (or other graspable object) to pick up.
        grasp_anchor: Anchor name on the object model to grasp at (also the anchor
            snapped onto the gripper).
        open_width_m: Fully-open gripper width before the approach.
        approach_width_m: Gripper width to pre-open to at the standoff, sized to
            clear the plate as the arm descends.
        grip_width_m: Final gripper width that clamps the plate.
        standoff_m: Straight-line standoff distance from the grasp anchor for the
            approach pose.
        lift_m: Extra height above the standoff for the first approach waypoint.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting wellplate_grab (anchor={grasp_anchor})")

    object_id = object.id

    # Swing in over the deck and open the gripper before touching the plate.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180, speed=0.8)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK, speed=0.8)
    set_gripper(arm="right_arm", width_m=open_width_m)

    # Resolve the grasp pose and its approach waypoints from the object model.
    pick = load_object_anchor(object_id, grasp_anchor)
    pick_xyz = pick["xyz"]
    pick_rpy = pick["rpy"]
    preapproach = anchor_preapproach(pick, standoff=0.05)
    preapproach_high = [preapproach[0], preapproach[1], preapproach[2] + lift_m]

    # Approach: lifted standoff -> standoff, pre-open, then descend onto the plate.
    move_arm(arm="right_arm", position=preapproach_high, orientation=pick_rpy, speed=70)
    move_arm(arm="right_arm", position=preapproach, orientation=pick_rpy, speed=40)
    set_gripper(arm="right_arm", width_m=approach_width_m)
    move_arm(arm="right_arm", position=pick_xyz, orientation=pick_rpy, speed=10)

    # Close on the plate, then assert the canonical grip and attach.
    set_gripper(arm="right_arm", width_m=grip_width_m)
    time.sleep(0.5)
    snap_plate_into_gripper(object_id, grasp_anchor=grasp_anchor)

    # Retract back to the standoff with the plate in hand.
    move_arm(arm="right_arm", position=preapproach, orientation=pick_rpy, speed=60)

    print_log("wellplate_grab completed")
    return {"success": True}
