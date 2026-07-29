from typing import Optional

from execution.execution_functions import *

# World-model prerequisites (see docs: Building a world / Adding an object / Anchors):
#   - `lid` object: a "grasp" anchor sized to the cap's outer diameter (it's a
#     push-fit, O-ring-sealed cap -- no threads, no hinge -- so the anchor's
#     `width` should be just under the cap's OD for a firm grip on the O-ring).
#   - `container` (or a separate rack object passed as `park`): a "lid_park"
#     anchor -- an empty spot the same height as the seated lid, oriented the
#     same way up, where the cap can be set down while the vial is open.

STANDOFF_M = 0.05
LIFT_CLEAR_M = 0.02
RELEASE_CLEARANCE_M = 0.005
TRANSIT_SPEED = 60


def open_container(
    container: SkillObject,
    lid: SkillObject,
    arm: str = "right_arm",
    speed: float = 20,
    park: Optional[SkillObject] = None,
    park_anchor: str = "lid_park",
):
    """Lift the lid off the container and set it down at a park spot.

    `lid` is resolved from its own current pose, so this works whether the
    lid is currently seated on `container` or already sitting somewhere else.
    """
    park = park or container

    grasp = load_object_anchor(lid.id, "grasp")
    pre = anchor_preapproach(grasp, standoff=STANDOFF_M)

    move_arm(arm=arm, position=pre, orientation=grasp["rpy"], speed=TRANSIT_SPEED)
    move_arm(arm=arm, position=grasp["xyz"], orientation=grasp["rpy"], speed=speed)
    set_gripper(arm=arm, width_m=grasp["width"])
    attach_object_to_arm(lid.id, arm)

    move_relative(arm=arm, delta_xyz=[0, 0, LIFT_CLEAR_M], speed=speed)

    target = load_object_anchor(park.id, park_anchor)
    target_pre = anchor_preapproach(target, standoff=STANDOFF_M)
    move_arm(arm=arm, position=target_pre, orientation=target["rpy"], speed=TRANSIT_SPEED)
    move_arm(arm=arm, position=target["xyz"], orientation=target["rpy"], speed=speed)
    set_gripper(arm=arm, width_m=target["width"] + RELEASE_CLEARANCE_M)
    detach_object_from_arm(lid.id)

    move_arm(arm=arm, position=target_pre, orientation=target["rpy"], speed=speed)

    set_world_state(container.id, {"lid_state": "open"})
    print_log(f"{container.id}: lid opened, parked on {park.id}/{park_anchor}")
    return {"success": True}
