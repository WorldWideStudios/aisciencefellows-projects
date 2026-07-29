from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN, RIGHT_FORWARD_DOWN

from .modules import load_object_anchor, move_arm, move_arm_js, print_log, set_gripper


ARM = "right_arm"
GRIPPER_OPEN_WIDTH_M = 0.07


def unload_test(
    openshelf: SkillObject,
    transit_speed: float = 40,
    slow_speed: float = 10,
):
    """Follow the taught unload path with the right arm and open the gripper.

    Args:
        openshelf: Open-shelf object carrying prepose_1, prepose_2, and
            prepose_3.
        transit_speed: Relative speed for the entry move to prepose_3.
        slow_speed: Relative speed for the taught path from prepose_3 to
            prepose_1 and back.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting unload_test "
        f"(arm={ARM}, transit_speed={transit_speed}, slow_speed={slow_speed})"
    )

    if transit_speed <= 0:
        raise ValueError("transit_speed must be positive")
    if slow_speed <= 0:
        raise ValueError("slow_speed must be positive")

    # Resolve the complete taught path before commanding any motion. This makes
    # a missing or mistyped anchor fail without moving either arm.
    prepose_3 = load_object_anchor(openshelf.id, "prepose_3")
    prepose_2 = load_object_anchor(openshelf.id, "prepose_2")
    prepose_1 = load_object_anchor(openshelf.id, "prepose_1")

    # Clear the inactive arm first, then route the right arm through the
    # standard forward/down transition pose before approaching the shelf.
    move_arm_js("left_arm", LEFT_FORWARD_DOWN, speed=0.5)
    move_arm_js(ARM, RIGHT_FORWARD_DOWN, speed=0.5)

    move_arm(
        arm=ARM,
        position=prepose_3["xyz"],
        orientation=prepose_3["rpy"],
        speed=transit_speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=prepose_2["xyz"],
        orientation=prepose_2["rpy"],
        speed=slow_speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=prepose_1["xyz"],
        orientation=prepose_1["rpy"],
        speed=slow_speed,
        wait=True,
    )

    set_gripper(arm=ARM, width_m=GRIPPER_OPEN_WIDTH_M)

    # Reverse the same taught Cartesian path and finish at prepose_3.
    move_arm(
        arm=ARM,
        position=prepose_2["xyz"],
        orientation=prepose_2["rpy"],
        speed=slow_speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=prepose_3["xyz"],
        orientation=prepose_3["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log(
        "unload_test completed; right gripper is open to 0.07 m "
        "and the arm is at prepose_3"
    )
    return {
        "success": True,
        "arm": ARM,
        "gripper_width_m": GRIPPER_OPEN_WIDTH_M,
        "final_anchor": "prepose_3",
    }
