import time

from utils import RIGHT_ARM_STOW_JOINTS

from .modules import (
    attach_object_to_arm,
    get_object_pose,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
)

ARM = "right_arm"
TIPBOX_TYPE = "tipbox_grey"
DEFAULT_TIPBOX = "tipbox_grey"
GRASP_ANCHOR = "Tipbox Openshelf Grasp Anchor"

# Hand-tuned pre-grasp joint pose: parks the arm on a feasible IK branch so the cartesian
# move onto the grasp solves (cartesian_movel fails from a bad start even where joints reach).
PRE_PICK_JOINTS = [1.616, -0.221, -0.552, -1.510, 1.657, 2.387]

GRASP_SPEED = 30
LIFT_SPEED = 150
STANDOFF_Z = 0.13
JS_SPEED = 0.5
OPEN_WIDTH_M = 0.11
GRIP_WIDTH_M = 0.05
CLOSE_STEPS = 6
STEP_DELAY_S = 0.15


def _find_tipbox_name() -> str:
    """Find the tipbox instance in the live world by object type; fall back to DEFAULT_TIPBOX."""
    try:
        from execution.execution_functions import hw

        for uid, entry in hw.world.objects.items():
            md = getattr(entry, "metadata", None) or {}
            if (md.get("type") if hasattr(md, "get") else None) == TIPBOX_TYPE:
                return md.get("name") or uid
    except Exception:
        pass
    return DEFAULT_TIPBOX


def pick_tipbox():
    """Right arm picks up the tipbox: pre-grasp joint pose, straight onto the grasp anchor,
    ease the gripper closed, attach, lift, then home."""
    print_log(runlog=True, runlog_type="step_start")

    obj_name = _find_tipbox_name()
    try:
        pose = get_object_pose(obj_name)
    except ValueError:
        pose = None

    grasp = load_object_anchor(obj_name, GRASP_ANCHOR)
    gx, gy, gz = grasp["xyz"]
    ori = grasp["rpy"]
    print_log(f"pick_tipbox: object={obj_name}, grasp xyz={grasp['xyz']}, rpy={ori}")

    move_arm_js(arm=ARM, joint_angles=PRE_PICK_JOINTS, speed=JS_SPEED)
    set_gripper(arm=ARM, width_m=OPEN_WIDTH_M)
    time.sleep(0.1)

    move_arm(arm=ARM, position=[gx, gy, gz], orientation=ori, speed=GRASP_SPEED, wait=True)
    time.sleep(0.2)

    span = GRIP_WIDTH_M - OPEN_WIDTH_M
    for i in range(CLOSE_STEPS):
        set_gripper(arm=ARM, width_m=OPEN_WIDTH_M + span * i / (CLOSE_STEPS - 1))
        time.sleep(STEP_DELAY_S)

    if pose is not None:
        try:
            attach_object_to_arm(pose["object_id"], arm=ARM)
        except ValueError:
            pass

    move_arm(arm=ARM, position=[gx, gy, gz + STANDOFF_Z], orientation=ori, speed=LIFT_SPEED, wait=True)
    move_arm_js(arm=ARM, joint_angles=RIGHT_ARM_STOW_JOINTS, speed=JS_SPEED)

    print_log("pick_tipbox complete")
    return {"success": True}
