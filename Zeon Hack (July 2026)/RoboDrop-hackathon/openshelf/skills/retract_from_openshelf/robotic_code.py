from .modules import (
    get_arm_pose,
    move_arm,
    print_log,
)

ARM = "right_arm"

# Straight-line pull-out of the OpenShelf IO box along world +Y (opposite the grab's
# -Y depth), so the arm — and the item attached to it — clears the shelf before any
# home move; enough to fully clear it, tune in sim.
RETRACT_Y = 0.20


def retract_from_openshelf():
    """Back the right arm straight out of the OpenShelf IO box before homing.

    Reads the arm's current pose and moves it +Y (out of the box) by RETRACT_Y,
    keeping orientation, so the arm (carrying the attached item) clears the shelf
    instead of dragging through it on the way home.
    """
    print_log(runlog=True, runlog_type="step_start")

    pose = get_arm_pose(arm=ARM)
    x, y, z = pose[:3]
    orientation = pose[3:]
    print_log(f"retract_from_openshelf: pulling out +Y {RETRACT_Y} m from {[x, y, z]}")

    move_arm(arm=ARM, position=[x, y + RETRACT_Y, z], orientation=orientation, speed=60, wait=True)

    print_log("retract_from_openshelf complete")
    return {"success": True}
