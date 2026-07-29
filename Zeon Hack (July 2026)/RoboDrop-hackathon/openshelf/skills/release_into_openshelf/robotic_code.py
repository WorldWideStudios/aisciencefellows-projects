import time

from .modules import (
    detach_object_from_arm,
    get_arm_pose,
    get_object_pose,
    move_arm,
    print_log,
    set_gripper,
)

ARM = "right_arm"
OBJECT = "tipbox_grey"

# Inverse of grab_openshelf_item: continue from the reached pose, push a little deeper -Y,
# ease the gripper open, detach so the box stays, then part-close so the jaws clear the hole.
RELEASE_OFFSET = [0.0, -0.05, 0.0]
GRIP_WIDTH_M = 0.05
OPEN_WIDTH_M = 0.11
RETRACT_WIDTH = 0.06          # part-close after release so the jaws fit back out the tight hole
OPEN_STEPS = 6
STEP_DELAY_S = 0.15
INSERT_SPEED = 30


def release_into_openshelf():
    """Release the carried tipbox into the OpenShelf IO box (the inverse of grab): continue
    from the reached pose, push a bit deeper, ease the gripper open, detach the box so it
    stays in the shelf, then part-close the jaws so they clear the hole on retract."""
    print_log(runlog=True, runlog_type="step_start")

    cur = get_arm_pose(arm=ARM)
    x, y, z = cur[:3]
    ori = cur[3:]
    dx, dy, dz = RELEASE_OFFSET
    print_log(f"release_into_openshelf: from {[round(v, 4) for v in cur[:3]]}, deeper by {RELEASE_OFFSET}")

    move_arm(arm=ARM, position=[x + dx, y + dy, z + dz], orientation=ori, speed=INSERT_SPEED, wait=True)

    span = OPEN_WIDTH_M - GRIP_WIDTH_M
    for i in range(OPEN_STEPS):
        set_gripper(arm=ARM, width_m=GRIP_WIDTH_M + span * i / (OPEN_STEPS - 1))
        time.sleep(STEP_DELAY_S)

    try:
        pose = get_object_pose(OBJECT)
        detach_object_from_arm(pose["object_id"])
    except ValueError:
        print_log(f"release_into_openshelf: object '{OBJECT}' not found — nothing to detach")

    set_gripper(arm=ARM, width_m=RETRACT_WIDTH)

    print_log("release_into_openshelf complete")
    return {"success": True}
