import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS
from .modules import (
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    anchor_preapproach
)

LEFT_ARM_INNER_SWING_JOINTS = [-2.663, -0.416, -1.340, 0.004, 1.750, 0.551]
LEFT_ARM_STOW_JOINTS = [-0.104, -0.681, -0.963, -0.018, 1.626, 1.459]
RIGHT_ARM_INNER_SWING_JOINT_180 = [1.675, -0.730, -0.815, 0.043, 1.567, 1.691]

def platesealer_platemax_place_seal(
    platesealer: SkillObject,
    approach_speed: float = 60,
    place_speed: float = 30,
):
    """Place a held seal onto the plate in the sealer with the left arm.

    Anchor-driven by the sealer's ``seal_place_*`` anchors. Carries the seal in with
    the gripper closed (align -> descend -> placed), opens to release it, retreats,
    goes back in to tap it down, then retreats again.

    Flow: seal_place_1_align -> seal_place_2_descend -> seal_place_3_placed, open the
    gripper, seal_place_4_retreat, seal_place_5_tap, seal_place_4_retreat.

    Args:
        platesealer: The plate sealer whose seal_place_* anchors drive the motion.
        release_width_m: Gripper width to open to when releasing the seal.
        approach_speed: Speed for the align / retreat moves.
        place_speed: Speed for the descent, placed, and tap moves.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log("Starting platesealer_platemax_place_seal")

    set_gripper(arm="left_arm", width_m=0.0)

    sealer_id = platesealer.id

    pre_preplace = load_object_anchor(sealer_id, "seal_place_0_pre_placement")
    preplace = load_object_anchor(sealer_id, "seal_place_0_placement")
    align = load_object_anchor(sealer_id, "seal_place_1_align")
    descend = load_object_anchor(sealer_id, "seal_place_2_descend")
    placed = load_object_anchor(sealer_id, "seal_place_3_placed")
    retreat = load_object_anchor(sealer_id, "seal_place_4_retreat")
    tap = load_object_anchor(sealer_id, "seal_place_5_tap")

    move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_INNER_SWING_JOINTS, speed=0.8)
    # move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_STOW_JOINTS, speed=0.8)

    # Carry the seal in with the gripper closed: align -> descend -> placed.
    move_arm(arm="left_arm", position=pre_preplace["xyz"], orientation=pre_preplace["rpy"], speed=approach_speed)
    move_arm(arm="left_arm", position=preplace["xyz"], orientation=preplace["rpy"], speed=approach_speed)
    move_arm(arm="left_arm", position=align["xyz"], orientation=align["rpy"], speed=approach_speed)
    move_arm(arm="left_arm", position=descend["xyz"], orientation=descend["rpy"], speed=place_speed)
    move_arm(arm="left_arm", position=placed["xyz"], orientation=placed["rpy"], speed=place_speed)

    # Move right arm to hold the seal
    set_gripper(arm="right_arm", width_m=0.0)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180)
    approach = load_object_anchor(sealer_id, "plate_hold")
    approach_preapproach = anchor_preapproach(approach, standoff=0.05)
    approach_preapproach_2 = anchor_preapproach(approach, standoff=0.05)
    move_arm(arm="right_arm", position=approach_preapproach, orientation=approach["rpy"], speed=70)
    move_arm(arm="right_arm", position=approach_preapproach_2, orientation=approach["rpy"], speed=70)
    move_arm(arm="right_arm", position=approach["xyz"], orientation=approach["rpy"], speed=5)

    # Release the seal and retreat
    set_gripper(arm="left_arm", width_m=0.005)
    time.sleep(0.5)
    move_arm(arm="left_arm", position=retreat["xyz"], orientation=retreat["rpy"], speed=approach_speed)

    # Move the right arm out of the way
    move_arm(arm="right_arm", position=approach_preapproach_2, orientation=approach["rpy"], speed=5)
    move_arm(arm="right_arm", position=approach_preapproach, orientation=approach["rpy"], speed=70)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_INNER_SWING_JOINT_180)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_STOW_JOINTS)

    # Retreat, go back in to tap the seal down, then retreat again.
    move_arm(arm="left_arm", position=tap["xyz"], orientation=tap["rpy"], speed=place_speed)
    move_arm(arm="left_arm", position=retreat["xyz"], orientation=retreat["rpy"], speed=approach_speed)

    move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_STOW_JOINTS, speed=0.8)

    print_log("platesealer_platemax_place_seal completed")
    return {"success": True}
