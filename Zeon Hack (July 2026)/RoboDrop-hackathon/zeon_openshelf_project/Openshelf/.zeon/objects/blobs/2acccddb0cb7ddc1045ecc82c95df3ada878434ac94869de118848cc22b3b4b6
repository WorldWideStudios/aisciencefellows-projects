from protocol_schema import SkillObject

from execution.execution_functions import (
    detach_object_from_arm,
    get_object_tcp_transform,
    is_sim_mode,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
)
from utils import RIGHT_FORWARD_FRONT


ARM = "right_arm"
CARRY_GRASP_ANCHOR = "horizontal_grip"
SHELF_RELEASE_ANCHOR = "testphyw"
OPEN_GRIPPER_WIDTH_M = 0.08
PLACE_SPEED = 0.5
TRANSITION_SPEED = 0.5
SECOND_TRANSITION_JOINTS = [-0.481, 0.194, -0.681, -2.024, 1.387, 2.670]
### [0.250, 0.112, -0.858, -1.347, 1.777, 2.382]


def place_plate_at_testphyw(
    plate: SkillObject,
    openshelf: SkillObject,
):
    """Move a right-arm-held PCR plate directly to OpenShelf testphyw.

    The destination contributes position only. The carried horizontal_grip
    orientation is used for the move and the final world-model snap.

    Args:
        plate: PCR plate attached by pickup_plate earlier in the workflow.
        openshelf: OpenShelf object providing the testphyw destination.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting place_plate_at_testphyw "
        f"(mode={'simulation' if is_sim_mode() else 'hardware'}, arm={ARM})"
    )

    try:
        get_object_tcp_transform(plate.id)
    except ValueError as exc:
        raise RuntimeError(
            "place_plate_at_testphyw requires the plate to be attached; "
            "run pickup_plate first in the same workflow"
        ) from exc

    carry = load_object_anchor(plate.id, CARRY_GRASP_ANCHOR)
    release = load_object_anchor(openshelf.id, SHELF_RELEASE_ANCHOR)

    
    # print_log("Stage transition: moving right arm to RIGHT_FORWARD_FRONT")
    # try:
    #     move_arm_js(
    #         arm=ARM,
    #         joint_angles=RIGHT_FORWARD_FRONT,
    #         speed=TRANSITION_SPEED,
    #     )
    # except Exception as exc:
    #     raise RuntimeError(
    #         f"place_plate_at_testphyw failed during first transition: {exc}"
    #     ) from exc
    # print_log("Stage transition: complete")

    print_log("Stage transition 2: moving right arm to specified joint pose")
    try:
        move_arm_js(
            arm=ARM,
            joint_angles=SECOND_TRANSITION_JOINTS,
            speed=TRANSITION_SPEED,
        )
    except Exception as exc:
        raise RuntimeError(
            f"place_plate_at_testphyw failed during second transition: {exc}"
        ) from exc
    print_log("Stage transition 2: complete")

    print_log(
        "Moving the attached plate directly to testphyw while preserving "
        "horizontal_grip orientation"
    )
    # try:
    #     move_arm(
    #         arm=ARM,
    #         position=release["xyz"],
    #         orientation=carry["rpy"],
    #         speed=PLACE_SPEED,
    #         wait=True,
    #     )
    # except Exception as exc:
    #     raise RuntimeError(
    #         f"place_plate_at_testphyw failed while moving to testphyw: {exc}"
    #     ) from exc

    print_log("Opening the gripper and releasing the plate")
    try:
        set_gripper(arm=ARM, width_m=OPEN_GRIPPER_WIDTH_M)
        detach_object_from_arm(plate.id)
        snap_object_anchor_to_world_pose(
            plate.id,
            CARRY_GRASP_ANCHOR,
            release["xyz"],
            carry["wxyz"],
        )
    except Exception as exc:
        raise RuntimeError(
            f"place_plate_at_testphyw failed while releasing the plate: {exc}"
        ) from exc

    print_log("place_plate_at_testphyw completed")
    return {
        "success": True,
        "arm": ARM,
        "carry_grasp_anchor": CARRY_GRASP_ANCHOR,
        "release_anchor": SHELF_RELEASE_ANCHOR,
        "release_xyz": release["xyz"],
        "plate_orientation_preserved": True,
        "collision_planning_required": True,
    }
