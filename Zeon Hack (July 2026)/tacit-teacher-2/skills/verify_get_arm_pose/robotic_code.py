from .modules import get_arm_pose, print_log


def verify_get_arm_pose():
    """Diagnostic: call get_arm_pose() for both arms and log the result.

    Read-only — get_arm_pose "does not move the arm" per its own docs. This
    skill exists only to confirm the function actually exists and returns a
    sensible value; delete it once confirmed.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting verify_get_arm_pose")

    left = get_arm_pose("left_arm")
    print_log(f"get_arm_pose('left_arm') = {list(left)}")

    right = get_arm_pose("right_arm")
    print_log(f"get_arm_pose('right_arm') = {list(right)}")

    print_log("verify_get_arm_pose completed")
    return {"success": True, "left_arm_pose": list(left), "right_arm_pose": list(right)}
