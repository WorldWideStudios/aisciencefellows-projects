from execution.execution_functions import *


def place_on_stand(
    plate: SkillObject,
    stand: SkillObject,
    stand_anchor: str = "plate_nest",
    plate_anchor: str = "nest_base",
    arm: str = "right_arm",
    approach_m: float = 0.10,
    settle_m: float = 0.0065,
    retreat_m: float = 0.10,
    speed: float = 30.0,
    place_speed: float = 8.0,
):
    """Seat a plate on the tagged stand and release, so the other arm can take it.

    This is the regrasp point of the chain. The plate is put down rather than handed over,
    which removes any two-arm coordination and -- because the stand carries AprilTags --
    lets the next step MEASURE where the plate ended up instead of trusting a snap.

    The release happens before the snap. Snapping asserts a pose and measures nothing, so
    snapping first renders a perfectly seated plate whether or not the gripper let go where
    you think it did.

    Args:
        plate: The held plate.
        stand: The tagged stand.
        stand_anchor: Seat anchor on the stand.
        plate_anchor: Seat anchor on the plate that meets it.
        arm: Arm holding the plate.
        approach_m: Standoff above the seat before descending.
        settle_m: Extra depth along the approach before releasing.
        retreat_m: Clearance to gain after releasing.
        speed: Relative speed for the approach.
        place_speed: Relative speed for the descent.
    """
    print_log(runlog=True, runlog_type="step_start")

    if arm not in ("left_arm", "right_arm"):
        print_log(f"place_on_stand: refusing invalid arm {arm!r}")
        return {"success": False, "reason": "invalid_arm"}

    seat = load_object_anchor(stand.id, stand_anchor)
    rpy = seat["rpy"]
    print_log(f"place_on_stand: {stand.id}.{stand_anchor} xyz={seat['xyz']}")

    pre = anchor_preapproach(seat, standoff=approach_m)
    move_arm(arm, pre, rpy, speed=speed)
    move_arm(arm, seat["xyz"], rpy, speed=place_speed)
    pause_aware_sleep(0.4)

    width = seat.get("width")
    set_gripper(arm, (width + 0.030) if width else 0.080)
    detach_object_from_arm(plate.id)
    snap_object_anchor_to_world_pose(plate.id, plate_anchor, seat["xyz"], seat["wxyz"])

    move_relative(arm, [0.0, 0.0, retreat_m], speed=speed)

    print_log(f"place_on_stand: {plate.id} released onto {stand.id}.{stand_anchor}")
    return {"success": True, "plate": plate.id, "on": stand_anchor, "arm": arm}
