import time

from execution.skill_editing import shared_state
from protocol_schema import SkillObject
from utils import RIGHT_FORWARD_DOWN

from .modules import detach_object_from_arm, move_arm_js, print_log, set_gripper


def wellplate_release(plate: SkillObject):
    """Release a held plate and move the right arm out of the way.

    Opens the gripper, detaches the plate from the arm, and retreats the
    right arm to its RIGHT_FORWARD_DOWN staging pose. The plate is not
    relocated — it stays exactly wherever it currently sits (e.g. wherever
    wellplate_hold left it); this only clears the arm. Never touches the left
    arm.

    Args:
        plate: The plate object currently held by the right arm (from
            wellplate_hold or wellplate_grab).
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting wellplate_release")

    plate_id = plate.id

    grasp_state = getattr(shared_state, "wellplate_grab_grasp", None) or {}
    grasp_width = grasp_state.get("width")
    if grasp_width is None:
        grasp_width = 0.05
    release_width = grasp_width + 0.02

    set_gripper(arm="right_arm", width_m=release_width)
    time.sleep(0.3)

    try:
        detach_object_from_arm(plate_id)
    except Exception as e:
        print_log(f"detach_object_from_arm failed: {e}")

    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)
    set_gripper(arm="right_arm", width_m=0.0)

    print_log("wellplate_release completed — right arm clear")
    return {"success": True}
