from .modules import (
    get_arm_pose,
    load_object_anchor,
    move_arm,
    print_log,
)

ARM = "right_arm"
OBJECT = "openshelf"
ANCHOR = "Openshelf Plate Anchor"

# The IO box is a tight square, so enter along a single straight line in world Y (the
# mirror of retract's +Y pull-out): a standoff just outside, then straight -Y in.
ENTER_STANDOFF = [0.0, 0.10, 0.0]
LOAD_Z_OFFSET = 0.025          # rest the box slightly above the plate anchor so it clears the opening
APPROACH_SPEED = 50
ENTER_SPEED = 30


def enter_openshelf():
    """Carry the held item into the OpenShelf IO box: reach a standoff just outside at the
    plate anchor's orientation, then ease straight -Y into the tight square without
    re-orienting (the mirror of retract_from_openshelf)."""
    print_log(runlog=True, runlog_type="step_start")

    a = load_object_anchor(OBJECT, ANCHOR)
    ax, ay, az = a["xyz"][0], a["xyz"][1], a["xyz"][2] + LOAD_Z_OFFSET
    ori = a["rpy"]
    sx, sy, sz = ENTER_STANDOFF
    print_log(f"enter_openshelf: plate anchor xyz={a['xyz']} rpy={ori}")

    move_arm(arm=ARM, position=[ax + sx, ay + sy, az + sz], orientation=ori, speed=APPROACH_SPEED, wait=True)

    cur = get_arm_pose(arm=ARM)
    cx, cy, cz = cur[:3]
    move_arm(arm=ARM, position=[cx - sx, cy - sy, cz - sz], orientation=cur[3:], speed=ENTER_SPEED, wait=True)

    print_log("enter_openshelf complete")
    return {"success": True}
