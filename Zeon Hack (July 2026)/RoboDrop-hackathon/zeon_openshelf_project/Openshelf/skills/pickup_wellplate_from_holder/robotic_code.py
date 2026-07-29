from protocol_schema import SkillObject

from execution.execution_functions import (
    anchor_preapproach,
    attach_object_to_arm,
    clear_skill_variable,
    is_sim_mode,
    load_object_anchor,
    move_arm,
    move_arm_js,
    move_relative,
    print_log,
    set_gripper,
    set_skill_variable,
    snap_object_anchor_to_world_pose,
)
from utils import RIGHT_FORWARD_DOWN


ARM = "right_arm"
TRANSFER_STATE_KEY = "move_wellplate_to_openshelf.transfer"
ORIENTATION_DOT_MIN = 0.99999


def _quaternion_alignment(first, second):
    if len(first) != 4 or len(second) != 4:
        raise ValueError("Anchor quaternions must contain four values")
    first_norm = sum(value * value for value in first) ** 0.5
    second_norm = sum(value * value for value in second) ** 0.5
    if first_norm <= 0 or second_norm <= 0:
        raise ValueError("Anchor quaternions must be non-zero")
    return abs(
        sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm)
    )


def pickup_wellplate_from_holder(
    plate: SkillObject,
    holder: SkillObject,
    pickup_grasp_anchor: str = "right_side_grasp_flipped",
    staging_right_tcp_anchor: str = "plate_stage_right_side_flipped_tcp",
    lift_m: float = 0.08,
    speed: float = 30.0,
    slow_speed: float = 10.0,
):
    """Pick a PCR wellplate from its exposed edge and stage it on the right arm.

    The horizontal side grasp keeps the right-arm wrist out of the volume above
    the plate that must enter OpenShelf. The source grasp and holder-relative
    staging TCP have the same world orientation, so the plate stays level and
    keeps its full orientation throughout pickup, lift, and staging.

    Args:
        plate: PCR wellplate seated in the tagged holder.
        holder: Tagged holder providing the right-arm staging TCP anchor.
        pickup_grasp_anchor: Plate side grasp used for pickup by the right arm.
        staging_right_tcp_anchor: Right-arm side-grip TCP pose clear of the holder.
        lift_m: Initial world-Z lift after grasping, in metres.
        speed: Relative speed for free-space arm moves.
        slow_speed: Relative speed for grasp and lift moves.
    """
    pickup_grasp_anchor = pickup_grasp_anchor.strip()
    staging_right_tcp_anchor = staging_right_tcp_anchor.strip()

    anchor_names = {
        "pickup_grasp_anchor": pickup_grasp_anchor,
        "staging_right_tcp_anchor": staging_right_tcp_anchor,
    }
    for parameter, anchor_name in anchor_names.items():
        if not anchor_name:
            raise ValueError(f"{parameter} must name an object-model anchor")
    if not 0.02 <= lift_m <= 0.12:
        raise ValueError("lift_m must be between 0.02 and 0.12 metres")
    if speed <= 0 or slow_speed <= 0:
        raise ValueError("speed and slow_speed must be positive")

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting pickup_wellplate_from_holder "
        f"(mode={'simulation' if is_sim_mode() else 'hardware'}, "
        f"arm={ARM}, grasp={pickup_grasp_anchor})"
    )
    clear_skill_variable(TRANSFER_STATE_KEY)

    grasp = load_object_anchor(plate.id, pickup_grasp_anchor)
    staging = load_object_anchor(holder.id, staging_right_tcp_anchor)
    if grasp["width"] <= 0:
        raise ValueError(
            f"plate anchor {pickup_grasp_anchor!r} needs a positive grasp width"
        )
    staging_alignment = _quaternion_alignment(grasp["wxyz"], staging["wxyz"])
    if staging_alignment < ORIENTATION_DOT_MIN:
        raise ValueError(
            f"staging anchor {staging_right_tcp_anchor!r} would rotate the plate "
            f"(quaternion alignment={staging_alignment:.8f})"
        )

    pre_grasp = anchor_preapproach(grasp)
    open_width = min(0.08, grasp["width"] + 0.02)

    print_log(
        "Staging the right arm, opening its gripper, and approaching "
        "the exposed plate edge"
    )
    move_arm_js(
        arm=ARM,
        joint_angles=RIGHT_FORWARD_DOWN,
        speed=0.5,
    )
    set_gripper(arm=ARM, width_m=open_width)
    move_arm(
        arm=ARM,
        position=pre_grasp,
        orientation=grasp["rpy"],
        speed=speed,
        wait=True,
    )
    move_arm(
        arm=ARM,
        position=grasp["xyz"],
        orientation=grasp["rpy"],
        speed=slow_speed,
        wait=True,
    )

    print_log("Closing the gripper and asserting the canonical plate grip")
    set_gripper(arm=ARM, width_m=grasp["width"])
    snap_object_anchor_to_world_pose(
        plate.id,
        pickup_grasp_anchor,
        grasp["xyz"],
        grasp["wxyz"],
    )
    attach_object_to_arm(plate.id, ARM)

    print_log("Lifting the attached plate clear of the holder")
    move_relative(
        arm=ARM,
        delta_xyz=[0.0, 0.0, lift_m],
        speed=slow_speed,
        wait=True,
    )

    print_log("Staging the level plate for direct right-arm transport")
    move_arm(
        arm=ARM,
        position=staging["xyz"],
        orientation=staging["rpy"],
        speed=speed,
        wait=True,
    )

    set_skill_variable(
        TRANSFER_STATE_KEY,
        {
            "plate_id": plate.id,
            "holder_id": holder.id,
            "arm": ARM,
            "pickup_grasp_anchor": pickup_grasp_anchor,
            "grasp_width_m": grasp["width"],
            "staging_right_tcp_anchor": staging_right_tcp_anchor,
            "carry_wxyz": list(staging["wxyz"]),
            "orientation_dot_min": ORIENTATION_DOT_MIN,
            "plate_level": True,
            "plate_orientation_preserved": True,
            "collision_planning_required": True,
        },
    )

    print_log("pickup_wellplate_from_holder completed")
    return {
        "success": True,
        "arm": ARM,
        "pickup_grasp_anchor": pickup_grasp_anchor,
        "staging_right_tcp_anchor": staging_right_tcp_anchor,
        "lift_m": lift_m,
        "staging_orientation_alignment": staging_alignment,
        "plate_level": True,
        "plate_orientation_preserved": True,
    }
