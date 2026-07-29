import time

from .modules import (
    attach_object_to_arm,
    get_arm_pose,
    get_object_pose,
    move_arm,
    print_log,
    set_gripper,
)

ARM = "right_arm"
OBJECT = "tipbox_grey"      # the dispensed item at the plate anchor (matches snap_to_openshelf)

# Continue from where reach_openshelf left the arm (already at the plate anchor,
# camera-up). Keep THAT orientation and just push a little deeper into the IO box
# along world -Y so the jaws surround the item, then ease the gripper closed. This
# avoids re-deriving a different orientation (which made the arm reorient and fail IK).
APPROACH_OFFSET = [0.0, -0.05, 0.0]

# Gradual close: ease the jaws from open to GRIP_WIDTH_M in even steps rather than
# slamming the closed width in one shot. Tune in sim.
OPEN_WIDTH_M = 0.11
GRIP_WIDTH_M = 0.05
CLOSE_STEPS = 6
STEP_DELAY_S = 0.15
DESCEND_SPEED = 30          # careful descent speed


def grab_openshelf_item():
    """Grab the dispensed item at the plate anchor with the right gripper.

    Continues from reach_openshelf's pose (arm at the plate anchor, camera-up):
    keeps that exact orientation, pushes a bit deeper into the box, eases the gripper
    closed, then attaches the item so it travels with the arm.
    """
    print_log(runlog=True, runlog_type="step_start")

    # Current pose (right where reach left us) — reuse its orientation, don't reorient.
    cur = get_arm_pose(arm=ARM)
    x, y, z = cur[:3]
    ori = cur[3:]
    dx, dy, dz = APPROACH_OFFSET
    print_log(f"grab_openshelf_item: from {[round(v,4) for v in cur[:3]]} rpy={[round(v,4) for v in ori]}, deeper by {APPROACH_OFFSET}")

    move_arm(arm=ARM, position=[x + dx, y + dy, z + dz], orientation=ori, speed=DESCEND_SPEED, wait=True)

    span = GRIP_WIDTH_M - OPEN_WIDTH_M
    for i in range(CLOSE_STEPS):
        width = OPEN_WIDTH_M + span * i / (CLOSE_STEPS - 1)
        set_gripper(arm=ARM, width_m=width)
        time.sleep(STEP_DELAY_S)
    print_log(f"grab_openshelf_item: gripper eased to {GRIP_WIDTH_M} m")

    try:
        pose = get_object_pose(OBJECT)
        attach_object_to_arm(pose["object_id"], arm=ARM)
        print_log(f"grab_openshelf_item: attached {OBJECT} to {ARM}")
    except ValueError:
        print_log(f"grab_openshelf_item: object '{OBJECT}' not found — gripper closed but nothing to attach")

    print_log("grab_openshelf_item complete")
    return {"success": True}
