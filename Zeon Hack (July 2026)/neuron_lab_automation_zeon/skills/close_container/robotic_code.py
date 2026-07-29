from typing import Optional

from execution.execution_functions import *

# World-model prerequisites (see docs: Building a world / Adding an object / Anchors):
#   - `lid` object: the same "grasp" anchor used by open_container.
#   - `container`: a "lid_seat" anchor at the vial's mouth, oriented so
#     lowering the lid straight down along its own Z compresses the O-ring.
#   - `park` (defaults to `container`): the "lid_park" anchor the lid is
#     currently sitting at, from a prior open_container call.

STANDOFF_M = 0.05
LIFT_CLEAR_M = 0.02
RELEASE_CLEARANCE_M = 0.005
TRANSIT_SPEED = 60


def close_container(
    container: SkillObject,
    lid: SkillObject,
    arm: str = "right_arm",
    speed: float = 20,
    park: Optional[SkillObject] = None,
    park_anchor: str = "lid_park",
):
    """Pick the lid up from its park spot and press it back onto the container."""
    park = park or container

    grasp = load_object_anchor(lid.id, "grasp")
    pre = anchor_preapproach(grasp, standoff=STANDOFF_M)

    move_arm(arm=arm, position=pre, orientation=grasp["rpy"], speed=TRANSIT_SPEED)
    move_arm(arm=arm, position=grasp["xyz"], orientation=grasp["rpy"], speed=speed)
    set_gripper(arm=arm, width_m=grasp["width"])
    attach_object_to_arm(lid.id, arm)

    move_relative(arm=arm, delta_xyz=[0, 0, LIFT_CLEAR_M], speed=speed)

    seat = load_object_anchor(container.id, "lid_seat")
    seat_pre = anchor_preapproach(seat, standoff=STANDOFF_M)
    move_arm(arm=arm, position=seat_pre, orientation=seat["rpy"], speed=TRANSIT_SPEED)
    move_arm(arm=arm, position=seat["xyz"], orientation=seat["rpy"], speed=speed)
    set_gripper(arm=arm, width_m=seat["width"] + RELEASE_CLEARANCE_M)
    detach_object_from_arm(lid.id)

    move_arm(arm=arm, position=seat_pre, orientation=seat["rpy"], speed=speed)

    set_world_state(container.id, {"lid_state": "closed"})
    print_log(f"{container.id}: lid closed")
    return {"success": True}
