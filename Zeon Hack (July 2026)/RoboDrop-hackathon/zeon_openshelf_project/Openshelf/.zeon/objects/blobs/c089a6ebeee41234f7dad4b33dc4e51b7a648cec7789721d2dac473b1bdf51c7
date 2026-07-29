import time

from execution.skill_editing import shared_state
from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN

from .modules import (
    detach_object_from_arm,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    snap_object_to_world_pose,
)

def epipette_place(
    pipette: SkillObject,
    grasp_anchor: str = "grab",
    prepose: str = "grab_prepose",
    postpose: str = "grab_postpose",
):
    """Place a pipette back down at a named grasp anchor and release it.

    Inverse of epipette_grab: approach the postpose from 5 cm above and descend
    onto it (mirroring grab's 5 cm lift off the postpose), continue down to the
    grasp anchor (home — where the pipette was grabbed), open the gripper to
    release, detach the pipette from the arm and restore it to its home world pose,
    then retreat via the prepose. Any pipette with a grasp anchor in its object
    model works with no code change.

    When epipette_grab ran earlier it stashes the world-frame prepose/postpose
    points it travelled through (captured while the pipette was at its start
    location); this skill prefers those saved points so it returns along the exact
    path grab took, falling back to re-resolving the object-model anchors if none
    were stashed.

    Args:
        pipette: The pipette object to place.
        grasp_anchor: Anchor name on the pipette's object model to place at
            (both shipped pipettes use 'grab').
        prepose: Optional anchor name to move to before/after the place pose. Pass
            an empty string to skip it; if the anchor is not on the object model it
            is skipped with a warning.
        postpose: Optional anchor name to move to before descending to the grasp
            (the reverse of grab's in-place reorient). Pass an empty string to skip
            it; skipped with a warning if unavailable.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting epipette_place (anchor={grasp_anchor}, prepose={prepose}, postpose={postpose})")

    object_id = pipette.id

    # Prefer the world-frame waypoints epipette_grab captured at the pipette's
    # start location; fall back to re-resolving the object-model anchor. Returns
    # None if neither is available (that waypoint is then skipped).
    def _resolve(saved, anchor):
        if saved:
            return saved
        if anchor:
            try:
                a = load_object_anchor(object_id, anchor)
                return {"xyz": a["xyz"], "rpy": a["rpy"]}
            except (KeyError, ValueError) as e:
                print_log(f"Anchor '{anchor}' unavailable, skipping: {e}")
        return None

    def _goto(pose, speed):
        if not pose:
            return
        move_arm(
            arm="left_arm",
            position=pose["xyz"],
            orientation=pose["rpy"],
            speed=speed,
            wait=True,
        )

    def _above(pose, dz):
        """Same orientation, raised dz metres in world Z. None passes through."""
        if not pose:
            return None
        x, y, z = pose["xyz"]
        return {"xyz": [x, y, z + dz], "rpy": pose["rpy"]}

    pre_pose = _resolve(getattr(shared_state, "epipette_grab_prepose", None), prepose)
    post_pose = _resolve(getattr(shared_state, "epipette_grab_postpose", None), postpose)
    # The grasp/home point: prefer the pose epipette_grab resolved while the
    # pipette was home. Re-resolving the anchor now would compute it against the
    # pipette's current (attached, elevated) world pose and send the arm too high.
    place_pose = _resolve(getattr(shared_state, "epipette_grab_grasp", None), grasp_anchor)

    move_arm_js(arm="left_arm", joint_angles=LEFT_FORWARD_DOWN, speed=0.5)
    _goto(pre_pose, 50)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    # Approach the postpose from 5 cm above and descend onto it — the reverse of
    # grab, which lifts 5 cm straight up after reaching the postpose.
    _goto(_above(post_pose, 0.05), 30)
    _goto(post_pose, 30)

    # Descend to the place pose (home — where the pipette was grabbed) and release.
    _goto(place_pose, 30)
    time.sleep(0.5)
    set_gripper(arm="left_arm", width_m=0.05)
    time.sleep(0.5)

    # Detach from the arm and snap the pipette back to its home world pose
    # (stashed by epipette_grab). Best-effort: never let cleanup fail the place.
    try:
        detach_object_from_arm(object_id)
    except Exception as e:
        print_log(f"detach_object_from_arm failed: {e}")

    home = getattr(shared_state, "epipette_grab_home_pose", None)
    if home:
        try:
            snap_object_to_world_pose(home["object_id"], home["xyz"], home["wxyz"])
        except Exception as e:
            print_log(f"snap_object_to_world_pose failed: {e}")
    else:
        print_log("epipette_grab_home_pose not set — skipping snap")

    # Retreat back up through the prepose waypoint.
    _goto(pre_pose, 50)

    set_gripper(arm="left_arm", width_m=0.0)
    time.sleep(0.1)

    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    print_log("epipette_place completed")
    return {"success": True}
