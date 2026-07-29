import time

from execution.skill_editing import shared_state
from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN, object_display_name

from .modules import (
    attach_object_to_arm,
    get_object_pose,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    set_skill_variable,
    move_relative,
)

def epipette_grab(
    pipette: SkillObject,
    grasp_anchor: str = "grab",
    prepose: str = "grab_prepose",
    postpose: str = "grab_postpose",
):
    """Pick up a pipette with the left arm at a named grasp anchor.

    The pipette object and the anchors are parameters, so any pipette with a
    grasp anchor in its object model works with no code change. If ``prepose`` names an anchor on the object model, the arm
    moves there first (an approach pose), then to the grasp pose and grabs.

    Args:
        pipette: The pipette object to grab.
        grasp_anchor: Anchor name on the pipette's object model to grasp at
            (both shipped pipettes use 'grab').
        prepose: Optional anchor name to move to before the grasp pose. Pass an
            empty string to skip it; if the anchor is not on the object model it
            is skipped with a warning.
        postpose: Optional anchor name to move to immediately after grabbing (an
            in-place reorient before retracting). Pass an empty string to skip it;
            if the anchor is not on the object model it is skipped with a warning.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting epipette_grab (anchor={grasp_anchor}, prepose={prepose}, postpose={postpose})")

    object_id = pipette.id

    # World-frame waypoints this grab travels through, captured while the pipette
    # is still at its start location so a later epipette_place can retrace them in
    # reverse. Left as None if the anchor is unavailable.
    saved_prepose = None
    saved_postpose = None

    # Best-effort home-pose stash so a later put-back skill can return the
    # pipette. get_object_pose matches by display name, not UUID, so resolve the
    # name first; never let this fail the grab.
    try:
        name = object_display_name(pipette)
        home = get_object_pose(name)
        shared_state.epipette_grab_home_pose = {
            "object_id": home["object_id"],
            "xyz": home["xyz"],
            "wxyz": home["wxyz"],
        }
    except Exception:
        pass

    grasp = load_object_anchor(object_id, grasp_anchor)
    pick_xyz = grasp["xyz"]
    pick_ori = grasp["rpy"]
    set_skill_variable("epipette_grab_pose", {"xyz": pick_xyz, "ori": pick_ori})

    # Stash the grasp point resolved here (while the pipette is still at its home
    # location) so epipette_place descends to the real grab pose instead of
    # re-resolving the anchor against the pipette once it is attached to the arm
    # and elevated (which would yield an elevated, wrong point).
    shared_state.epipette_grab_grasp = {"xyz": pick_xyz, "rpy": pick_ori}

    move_arm_js(arm="left_arm", joint_angles=LEFT_FORWARD_DOWN, speed=0.5)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    set_gripper(arm="left_arm", width_m=0.05)
    time.sleep(0.1)

    # Optional prepose: move to an approach anchor before the grasp pose.
    if prepose:
        try:
            pre = load_object_anchor(object_id, prepose)
            saved_prepose = {"xyz": pre["xyz"], "rpy": pre["rpy"]}
            move_arm(
                arm="left_arm",
                position=pre["xyz"],
                orientation=pre["rpy"],
                speed=50,
                wait=True,
            )
        except (KeyError, ValueError) as e:
            print_log(f"Prepose anchor '{prepose}' unavailable, skipping: {e}")

    # Move to the grasp pose and grab.
    move_arm(
        arm="left_arm",
        position=pick_xyz,
        orientation=pick_ori,
        speed=30,
        wait=True,
    )
    time.sleep(0.5)
    set_gripper(arm="left_arm", width_m=0.035)
    time.sleep(0.1)

    try:
        attach_object_to_arm(object_id, arm="left_arm")
    except ValueError:
        pass

    # Optional postpose: reorient in place at the grasp point before retracting.
    if postpose:
        try:
            post = load_object_anchor(object_id, postpose)
            saved_postpose = {"xyz": post["xyz"], "rpy": post["rpy"]}
            move_arm(
                arm="left_arm",
                position=post["xyz"],
                orientation=post["rpy"],
                speed=30,
                wait=True,
            )
        except (KeyError, ValueError) as e:
            print_log(f"Postpose anchor '{postpose}' unavailable, skipping: {e}")

    move_relative(arm="left_arm", delta_xyz=[0.0, 0.0, 0.05], delta_rpy=None)

    set_gripper(arm="left_arm", width_m=0.012)
    time.sleep(0.2)
    # Stash the captured waypoints for epipette_place to retrace in reverse.
    shared_state.epipette_grab_prepose = saved_prepose
    shared_state.epipette_grab_postpose = saved_postpose

    if prepose:
        try:
            pre = load_object_anchor(object_id, prepose)
            move_arm(
                arm="left_arm",
                position=pre["xyz"],
                orientation=pre["rpy"],
                speed=50,
                wait=True,
            )
        except (KeyError, ValueError) as e:
            print_log(f"Prepose anchor '{prepose}' unavailable, skipping: {e}")

    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    print_log("epipette_grab completed")
    return {"success": True}
