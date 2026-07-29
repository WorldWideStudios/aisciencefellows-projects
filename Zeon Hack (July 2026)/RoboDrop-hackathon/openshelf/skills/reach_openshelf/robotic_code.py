from .modules import (
    load_object_anchor,
    move_arm,
    print_log,
)

ARM = "right_arm"
OBJECT = "openshelf"
ANCHOR = "Openshelf Plate Anchor"

# Approach speed (epipette_grey_pick uses 50 to approach); tune here.
REACH_SPEED = 50


def reach_openshelf():
    """Move the right arm to the OpenShelf plate anchor (single controlled move).

    Uses the plate anchor's orientation directly (camera-up), so the IK rolls the
    wrist into place as part of the move. Pure motion — shared by both directions:
    pair with a gripper CLOSE to receive an item, or an OPEN to load/release one.
    """
    print_log(runlog=True, runlog_type="step_start")

    a = load_object_anchor(OBJECT, ANCHOR)
    print_log(f"reach_openshelf: anchor xyz={a['xyz']} rpy={a['rpy']}")

    move_arm(
        arm=ARM,
        position=[a["xyz"][0], a["xyz"][1], a["xyz"][2]],
        orientation=a["rpy"],
        speed=REACH_SPEED,
        wait=True,
    )

    print_log("reach_openshelf complete")
    return {"success": True}
