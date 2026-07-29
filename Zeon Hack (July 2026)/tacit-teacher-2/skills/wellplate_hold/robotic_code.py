import time

from execution.skill_editing import shared_state
from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN, object_display_name

from .modules import (
    anchor_preapproach,
    attach_object_to_arm,
    get_object_pose,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    set_skill_variable,
)


def wellplate_hold(
    plate: SkillObject,
    grasp_anchor: str = "hold_plate",
    prepose: str = "pre_hold_plate",
    standoff: float = 0.08,
):
    """Grip a wellplate at its grasp anchor and hold it there — no lift, no move.

    Same approach as ``wellplate_grab`` (stage, optional prepose, hover,
    descend, close the gripper, attach), but deliberately stops there: it
    never retracts or returns to a staging pose. The plate stays exactly
    where it already sits; only the gripper closes onto it. Use
    ``wellplate_grab`` instead when you actually want to pick the plate up
    and relocate it.

    Args:
        plate: The plate object to grip.
        grasp_anchor: Anchor name on the plate's object model to grip at.
        prepose: Optional anchor name to move to before the grasp anchor (a
            wider approach point clear of the plate). Pass an empty string to
            skip it; if the anchor is not on the object model it is skipped
            with a warning.
        standoff: Hover clearance, in metres, above the grasp anchor for the
            pre-grip approach pose.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting wellplate_hold (anchor={grasp_anchor}, standoff={standoff})")

    object_id = plate.id

    # Best-effort home-pose stash, mirroring wellplate_grab, in case a later
    # skill wants to know where this instance started. Never let it fail.
    try:
        name = object_display_name(plate)
        home = get_object_pose(name)
        shared_state.wellplate_grab_home_pose = {
            "object_id": home["object_id"],
            "xyz": home["xyz"],
            "wxyz": home["wxyz"],
        }
    except Exception:
        pass

    grasp = load_object_anchor(object_id, grasp_anchor)
    pick_xyz = grasp["xyz"]
    pick_ori = grasp["rpy"]
    width = grasp.get("width")
    if width is None:
        width = 0.05

    shared_state.wellplate_grab_grasp = {"xyz": pick_xyz, "rpy": pick_ori, "width": width}
    set_skill_variable("wellplate_grab_pose", {"xyz": pick_xyz, "ori": pick_ori})

    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)
    move_arm_js(arm="left_arm", joint_angles=LEFT_FORWARD_DOWN, speed=0.5)

    # Open past whichever is wider: the prepose anchor's width or the grasp's.
    open_width = width
    if prepose:
        try:
            pre_check = load_object_anchor(object_id, prepose)
            open_width = max(open_width, pre_check.get("width") or 0.0)
        except (KeyError, ValueError):
            pass
    set_gripper(arm="right_arm", width_m=open_width + 0.02)
    time.sleep(0.1)

    # Optional prepose: move to a wider approach anchor before narrowing in on
    # the grasp pose itself.
    if prepose:
        try:
            pre = load_object_anchor(object_id, prepose)
            move_arm(arm="right_arm", position=pre["xyz"], orientation=pre["rpy"], speed=50, wait=True)
        except (KeyError, ValueError) as e:
            print_log(f"Prepose anchor '{prepose}' unavailable, skipping: {e}")

    pre_xyz = anchor_preapproach(grasp, standoff=standoff)
    move_arm(arm="right_arm", position=pre_xyz, orientation=pick_ori, speed=50, wait=True)

    move_arm(arm="right_arm", position=pick_xyz, orientation=pick_ori, speed=30, wait=True)
    time.sleep(0.5)

    set_gripper(arm="right_arm", width_m=width)
    time.sleep(0.2)

    try:
        attach_object_to_arm(object_id, arm="right_arm")
    except ValueError:
        pass

    # Deliberately no retract and no return to a staging pose: the arm stays
    # right here, holding the plate down exactly where it already sits.
    print_log("wellplate_hold completed — plate held in place, not lifted")
    return {"success": True}
