import time

from protocol_schema import SkillObject
from utils import RIGHT_ARM_STOW_JOINTS, snap_plate_into_gripper

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
    update_object_joint_config,
)

# Plate reader lid-open angle for the revolute lid_joint (closed is 0.0).
LID_OPEN_ANGLE = 2.0386

# Long-side ("platereader grab") gripper widths, in metres — wellplate_grab style:
#   pre-open (prepose) to 4.5 cm to clear the grab feature on the descent, then
#   clamp (close) to 2.8 cm on the plate. Retune here if the grasp slips or fouls.
PREPOSE_JAW_M = 0.045
GRIP_WIDTH_M = 0.028
LIFT_M = 0.05

# Right-arm swing pose that clears the deck on the way in and out of the reader.
RIGHT_ARM_OUTER_SWING_JOINTS_180 = [-2.145, -0.450, -0.957, -0.036, 1.380, 4.183]
RIGHT_ARM_PLATE_PICK = [0.797, -0.376, -1.065, 0.012, 1.472, 0.813]
RIGHT_ARM_PLATE_PICK_UNWIND = [0.797, -0.376, -1.065, 0.012, 1.472, 0.813]

def platereader_unload(
    object: SkillObject,
    platereader: SkillObject,
    unload_anchor: str = "unload_plate",
    plate_grasp_anchor: str = "grasp_longside_platereader",
):
    """Pick a well plate out of the plate reader with the right arm.

    Reverse of platereader_load. Assumes the lid is already open (models
    lid_joint = open so the pose is clear — run platereader_open first). Grabs the
    plate at the reader's ``unload_anchor`` — the settled pose platereader_load leaves
    the plate at — with a wellplate_grab-style descent: swing in, pre-open the gripper
    to the platereader grab width, drop to a lifted standoff then the standoff,
    descend onto the grab pose, clamp, then assert the canonical grip via
    ``snap_plate_into_gripper`` (snaps ``plate_grasp_anchor`` onto the gripper and
    attaches) so the plate is held identically to every other pick. Lifts out, stows.

    Args:
        object: The well plate sitting in the reader, to pick back out.
        platereader: The plate reader to unload from.
        unload_anchor: Reader anchor to grab from (default 'unload_plate').
        plate_grasp_anchor: The plate's own grasp anchor to grip/snap by (default
            'grasp_longside_platereader'; use the plate family's grasp anchor).
    """
    print_log(runlog=True, runlog_type="step_start")
    reader_id = platereader.id
    plate_id = object.id
    print_log(f"Starting platereader_unload: plate {plate_id} <- {unload_anchor}")

    # Model the lid open so the grab pose is clear.
    update_object_joint_config(reader_id, {"lid_joint": LID_OPEN_ANGLE})

    # Resolve the grab pose (reader-frame) and its approach waypoints.
    grab = load_object_anchor(reader_id, unload_anchor)
    preapproach = anchor_preapproach(grab, standoff=0.05)
    preapproach_high = [preapproach[0], preapproach[1], preapproach[2] + LIFT_M]

    # Swing in with the gripper pre-opened to the platereader grab width.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK, speed=0.8)
    set_gripper(arm="right_arm", width_m=PREPOSE_JAW_M)

    # Approach: lifted standoff -> standoff -> descend onto the grab pose.
    move_arm(arm="right_arm", position=preapproach_high, orientation=grab["rpy"], speed=60)
    move_arm(arm="right_arm", position=preapproach, orientation=grab["rpy"], speed=40)
    move_arm(arm="right_arm", position=grab["xyz"], orientation=grab["rpy"], speed=10)

    # Clamp on the plate, then assert the canonical grip and attach.
    set_gripper(arm="right_arm", width_m=GRIP_WIDTH_M)
    time.sleep(0.5)
    snap_plate_into_gripper(plate_id, arm="right_arm", grasp_anchor=plate_grasp_anchor)

    # Lift out through the preapproach, then stow.
    move_arm(arm="right_arm", position=preapproach, orientation=grab["rpy"], speed=50)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK, speed=0.8)
    move_arm_js(arm="right_arm", joint_angles=RIGHT_ARM_PLATE_PICK_UNWIND, speed=0.8)

    print_log("platereader_unload completed")
    return {"success": True}
