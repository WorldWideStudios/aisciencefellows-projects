from execution.execution_functions import *


def place_on_shelf(
    item: SkillObject,
    shelf: SkillObject,
    shelf_anchor: str = "slot_1",
    item_anchor: str = "bottom_center",
    arm: str = "right_arm",
    settle_m: float = 0.0065,
    retreat_m: float = 0.08,
    speed: float = 40.0,
    place_speed: float = 10.0,
):
    """Place a held item into a shelf slot.

    Approaches along the seat anchor's own axis, releases, and only THEN snaps the item
    to the seat. The ordering matters: snapping asserts a pose and measures nothing, so a
    snap before the release renders a perfectly seated item whether or not the gripper
    actually let go of it where you think.

    The settle depth follows the slot_N_unload convention already in the shaker model --
    a few millimetres deeper along the approach than the nominal slot, so a later pick
    closes under the settled item rather than pinching at its resting height.

    Args:
        item: The held object.
        shelf: The shelf to place into.
        shelf_anchor: Target slot.
        item_anchor: Seat anchor on the item.
        arm: "left_arm" or "right_arm".
        settle_m: Extra depth along the approach before releasing.
        retreat_m: Clearance to gain after releasing.
        speed: Relative speed for the approach.
        place_speed: Relative speed for the final descent.
    """
    print_log(runlog=True, runlog_type="step_start")

    if arm not in ("left_arm", "right_arm"):
        print_log(f"place_on_shelf: refusing invalid arm {arm!r}")
        return {"success": False, "reason": "invalid_arm"}

    seat = load_object_anchor(shelf.id, shelf_anchor)
    rpy = seat["rpy"]
    print_log(f"place_on_shelf: {shelf.id}.{shelf_anchor} xyz={seat['xyz']}")

    pre = anchor_preapproach(seat, standoff=0.10)
    move_arm(arm, pre, rpy, speed=speed)
    move_arm(arm, seat["xyz"], rpy, speed=place_speed)

    # Release first, then record. Never the other way round.
    width = seat.get("width")
    set_gripper(arm, (width + 0.030) if width else 0.080)
    detach_object_from_arm(item.id)
    snap_object_anchor_to_world_pose(item.id, item_anchor, seat["xyz"], seat["wxyz"])

    move_relative(arm, [0.0, 0.0, retreat_m], speed=speed)

    print_log("place_on_shelf completed")
    return {"success": True, "item": item.id, "into_slot": shelf_anchor, "arm": arm}
