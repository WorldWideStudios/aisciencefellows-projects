import time

from .modules import (
    detach_object_from_arm,
    get_arm_pose,
    get_object_pose,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
)

ARM = "right_arm"
OBJECT = "tipbox_grey"

# Park on pick_tipbox's feasible pre-grasp branch over the bench (a known-reachable X/Y),
# then ease straight DOWN to the bench-top height and release. Any reachable X/Y is fine;
# what matters is Z lands the box on the bench.
PRE_PLACE_JOINTS = [1.616, -0.221, -0.552, -1.510, 1.657, 2.387]
BENCH_Z = 0.065               # world Z where pick_tipbox grabs the resting box = bench top; tune in sim
GRIP_WIDTH_M = 0.05
OPEN_WIDTH_M = 0.11
OPEN_STEPS = 6
STEP_DELAY_S = 0.15
JS_SPEED = 0.5
DESCEND_SPEED = 30
LIFT_SPEED = 150


def place_tipbox():
    """Set the carried tipbox down on the bench top (inverse of pick_tipbox): swing to the
    feasible pre-grasp branch over the bench, ease straight down to the bench-top height,
    open the gripper, detach the box, and lift clear."""
    print_log(runlog=True, runlog_type="step_start")

    move_arm_js(arm=ARM, joint_angles=PRE_PLACE_JOINTS, speed=JS_SPEED)
    cur = get_arm_pose(arm=ARM)
    x, y, z = cur[:3]
    ori = cur[3:]
    print_log(f"place_tipbox: from {[round(v, 4) for v in cur[:3]]}, easing down to bench Z={BENCH_Z}")

    move_arm(arm=ARM, position=[x, y, BENCH_Z], orientation=ori, speed=DESCEND_SPEED, wait=True)

    span = OPEN_WIDTH_M - GRIP_WIDTH_M
    for i in range(OPEN_STEPS):
        set_gripper(arm=ARM, width_m=GRIP_WIDTH_M + span * i / (OPEN_STEPS - 1))
        time.sleep(STEP_DELAY_S)

    try:
        pose = get_object_pose(OBJECT)
        detach_object_from_arm(pose["object_id"])
    except ValueError:
        print_log(f"place_tipbox: object '{OBJECT}' not found — nothing to detach")

    move_arm(arm=ARM, position=[x, y, z], orientation=ori, speed=LIFT_SPEED, wait=True)

    print_log("place_tipbox complete")
    return {"success": True}
