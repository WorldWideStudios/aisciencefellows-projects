from execution.execution_functions import *


def take_from_shelf(
    item: SkillObject,
    shelf: SkillObject,
    shelf_anchor: str = "slot_1",
    item_anchor: str = "grasp_top_1",
    arm: str = "right_arm",
    lift_m: float = 0.08,
    speed: float = 40.0,
    approach_speed: float = 10.0,
):
    """Pick an item out of a shelf slot.

    Reads width and standoff from the item's own grasp anchor rather than hard-coding
    them, so the same skill handles anything that has been scanned in. The approach
    direction also comes from the anchor: anchor_preapproach backs off along the anchor's
    local -Z, which is the tcp convention, so this works for a top grasp and a side grasp
    without branching on which one it is.

    Args:
        item: The object to pick up.
        shelf: The shelf holding it.
        shelf_anchor: Slot the item is currently seated in (recorded in the result).
        item_anchor: Grasp anchor on the item to use.
        arm: "left_arm" or "right_arm" -- any other value silently moves the RIGHT arm.
        lift_m: Vertical clearance to gain after closing.
        speed: Relative speed for the approach.
        approach_speed: Relative speed for the final close-in.
    """
    print_log(runlog=True, runlog_type="step_start")

    if arm not in ("left_arm", "right_arm"):
        print_log(f"take_from_shelf: refusing invalid arm {arm!r}")
        return {"success": False, "reason": "invalid_arm"}

    grasp = load_object_anchor(item.id, item_anchor)
    width = grasp.get("width")
    if width is None:
        print_log(f"take_from_shelf: {item.id}.{item_anchor} has no grasp width")
        return {"success": False, "reason": "no_grasp_width"}

    pre = anchor_preapproach(grasp)
    rpy = grasp["rpy"]
    print_log(f"take_from_shelf: {item.id}.{item_anchor} width={width}")

    set_gripper(arm, width + 0.010)
    move_arm(arm, pre, rpy, speed=speed)
    move_arm(arm, grasp["xyz"], rpy, speed=approach_speed)
    set_gripper(arm, width)
    attach_object_to_arm(item.id, arm)

    # delta_rpy omitted -> orientation is held, so the item cannot tilt on the way up.
    move_relative(arm, [0.0, 0.0, lift_m], speed=speed)

    print_log("take_from_shelf completed")
    return {"success": True, "item": item.id, "from_slot": shelf_anchor,
            "width": width, "arm": arm}
