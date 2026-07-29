from protocol_schema import SkillObject

from execution.execution_functions import (
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
)
from utils import RIGHT_FORWARD_DOWN


ARM = "right_arm"
ORIENTATION_DOT_MIN = 0.99999


def _quaternion_alignment(first, second):
    first_norm = sum(value * value for value in first) ** 0.5
    second_norm = sum(value * value for value in second) ** 0.5
    if first_norm <= 0 or second_norm <= 0:
        raise ValueError("Anchor quaternions must be non-zero")
    return abs(
        sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm)
    )


def preflight_right_arm_anchor(
    target: SkillObject,
    entry_anchor: str,
    target_anchor: str,
    speed: float = 20.0,
    slow_speed: float = 10.0,
):
    """Test a right-arm entry and target TCP pose with an empty gripper.

    Args:
        target: Object providing the entry and target TCP anchors.
        entry_anchor: Collision-clear anchor immediately before the target.
        target_anchor: Exact right-arm TCP pose to validate.
        speed: Relative speed for the entry move.
        slow_speed: Relative speed for the final target and retreat.
    """
    entry_anchor = entry_anchor.strip()
    target_anchor = target_anchor.strip()
    if not entry_anchor or not target_anchor:
        raise ValueError("entry_anchor and target_anchor must be non-empty")
    if speed <= 0 or slow_speed <= 0:
        raise ValueError("speed and slow_speed must be positive")

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Preflighting empty-gripper right-arm reach "
        f"(entry={entry_anchor}, target={target_anchor})"
    )

    entry = load_object_anchor(target.id, entry_anchor)
    destination = load_object_anchor(target.id, target_anchor)
    alignment = _quaternion_alignment(entry["wxyz"], destination["wxyz"])
    if alignment < ORIENTATION_DOT_MIN:
        raise ValueError(
            "The entry and destination anchors change orientation "
            f"(quaternion alignment={alignment:.8f})"
        )

    move_arm_js(arm=ARM, joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)
    set_gripper(arm=ARM, width_m=0.08)
    move_arm(
        arm=ARM,
        position=entry["xyz"],
        orientation=entry["rpy"],
        speed=speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=destination["xyz"],
        orientation=destination["rpy"],
        speed=slow_speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=entry["xyz"],
        orientation=entry["rpy"],
        speed=slow_speed,
        wait=True,
    )
    move_arm_js(arm=ARM, joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)

    print_log("Right-arm anchor preflight completed")
    return {
        "success": True,
        "arm": ARM,
        "entry_anchor": entry_anchor,
        "target_anchor": target_anchor,
        "orientation_alignment": alignment,
    }
