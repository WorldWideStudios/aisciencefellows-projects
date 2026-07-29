import time

from execution.skill_editing import shared_state
from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN

from .modules import (
    anchor_preapproach,
    detach_object_from_arm,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
)


def wellplate_place(
    plate: SkillObject,
    target: SkillObject,
    target_anchor: str = "top_center",
    rest_anchor: str = "object",
    standoff: float = 0.08,
):
    """Place a held wellplate onto a target object's named anchor and release it.

    Inverse of ``wellplate_grab``, but the destination is a different object's
    anchor rather than the plate's own home pose: hover ``standoff`` metres
    above ``target_anchor`` (e.g. a stand's ``top_center``), descend onto it,
    open the gripper, detach the plate from the arm, then snap the plate's
    ``rest_anchor`` onto the target anchor's resolved world pose so it settles
    exactly rather than trusting arm-placement error.

    ``rest_anchor`` deliberately defaults to the plate's ``object`` anchor (its
    table-placement frame, at the true bottom-center of the footprint) rather
    than the grasp anchor: the grasp anchor sits wherever the gripper closes on
    the plate (above the bottom, for a real grip), so snapping it onto
    ``target_anchor`` would leave the plate floating by that same height. Snapping
    the bottom-center anchor instead means the plate's bottom lands exactly at
    ``target_anchor``'s height with no gap, regardless of where it was grasped.
    Any target object with the named anchor works with no code change.

    Args:
        plate: The plate object currently held by the arm (from wellplate_grab).
        target: The object to place the plate onto (e.g. a plate stand).
        target_anchor: Anchor name on the target object model to place at —
            the target's true resting-surface anchor (e.g. a stand's
            ``top_center``), not a reachability-adjusted duplicate.
        rest_anchor: Anchor name on the plate's object model that is aligned
            onto ``target_anchor``'s world pose after release — the plate's
            own bottom-center reference, so the seated plate has no gap.
        standoff: Hover clearance, in metres, above the target anchor for the
            pre-place approach pose.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting wellplate_place (target_anchor={target_anchor})")

    plate_id = plate.id
    target_id = target.id

    dest = load_object_anchor(target_id, target_anchor)
    place_xyz = dest["xyz"]
    place_ori = dest["rpy"]

    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)
    move_arm_js(arm="left_arm", joint_angles=LEFT_FORWARD_DOWN, speed=0.5)

    pre_xyz = anchor_preapproach(dest, standoff=standoff)
    move_arm(arm="right_arm", position=pre_xyz, orientation=place_ori, speed=50, wait=True)

    move_arm(arm="right_arm", position=place_xyz, orientation=place_ori, speed=30, wait=True)
    time.sleep(0.5)

    # Release using the width wellplate_grab taught (falls back to a generous
    # open if this plate was never grabbed by that skill in this run).
    grasp_state = getattr(shared_state, "wellplate_grab_grasp", None) or {}
    grasp_width = grasp_state.get("width")
    if grasp_width is None:
        grasp_width = 0.05
    release_width = grasp_width + 0.02
    set_gripper(arm="right_arm", width_m=release_width)
    time.sleep(0.5)

    try:
        detach_object_from_arm(plate_id)
    except Exception as e:
        print_log(f"detach_object_from_arm failed: {e}")

    # Align the plate's bottom-center anchor exactly onto the target anchor's
    # world pose — this is what removes any gap, not just drift correction.
    try:
        snap_object_anchor_to_world_pose(plate_id, rest_anchor, place_xyz, dest["wxyz"])
    except Exception as e:
        print_log(f"snap_object_anchor_to_world_pose failed: {e}")

    move_arm(arm="right_arm", position=pre_xyz, orientation=place_ori, speed=50, wait=True)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    set_gripper(arm="right_arm", width_m=0.0)
    time.sleep(0.1)

    print_log("wellplate_place completed")
    return {"success": True}
