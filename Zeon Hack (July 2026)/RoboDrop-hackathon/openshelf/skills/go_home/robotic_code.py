from utils import LEFT_ARM_STOW_JOINTS, RIGHT_ARM_STOW_JOINTS

from .modules import (
    move_arm_js,
    print_log,
)


def go_home(arm: str = "right_arm", speed: float = 0.5):
    """Return an arm to its stow / home rest pose.

    Home is the shared stow pose from ``utils.py`` for the chosen arm.

    Args:
        arm: Which arm to home ('left_arm' or 'right_arm').
        speed: Joint-space move speed.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"go_home: returning {arm} to stow pose")

    joints = RIGHT_ARM_STOW_JOINTS if arm == "right_arm" else LEFT_ARM_STOW_JOINTS
    move_arm_js(arm=arm, joint_angles=joints, speed=speed)

    print_log("go_home complete")
    return {"success": True}
