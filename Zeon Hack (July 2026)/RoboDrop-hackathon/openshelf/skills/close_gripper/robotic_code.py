from .modules import (
    print_log,
    set_gripper,
)


def close_gripper(width_m: float = 0.0, arm: str = "right_arm"):
    """Close the gripper on the given arm.

    Args:
        width_m: Target jaw width in metres (0.0 = fully closed).
        arm: Which arm's gripper to close ('left_arm' or 'right_arm').
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"close_gripper: arm={arm}, width_m={width_m}")

    set_gripper(arm=arm, width_m=width_m)

    print_log("close_gripper complete")
    return {"success": True}
