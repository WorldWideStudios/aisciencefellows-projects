from utils import LEFT_ARM_STOW_JOINTS

from .modules import (
    move_arm_js,
    print_log,
)

# Right-arm home pose. Matches the start pose in epipette_grab (its skill-local
# _RIGHT_ARM_STOW_JOINTS), which keeps the right arm clear of the left arm's
# workspace and is intentionally distinct from the shared RIGHT_ARM_STOW_JOINTS
# in utils.
RIGHT_ARM_HOME_JOINTS = [-0.210, -0.680, -0.864, -0.026, 1.607, 4.496]


def arms_home(speed: float = 0.5):
    """Move both arms to their home (start) joint poses.

    Sends the arms to the same poses epipette_grab uses at its start: the left arm
    to the shared LEFT_ARM_STOW_JOINTS and the right arm to RIGHT_ARM_HOME_JOINTS.
    Takes no objects — a neutral reset for the start or end of a run. Moves left
    then right (same order as epipette_grab).

    Args:
        speed: Joint-move speed for both arms (matches epipette_grab's 0.5).
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting arms_home (speed={speed})")

    move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_STOW_JOINTS, speed=speed)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_HOME_JOINTS, speed=speed)

    print_log("arms_home completed")
    return {"success": True}
