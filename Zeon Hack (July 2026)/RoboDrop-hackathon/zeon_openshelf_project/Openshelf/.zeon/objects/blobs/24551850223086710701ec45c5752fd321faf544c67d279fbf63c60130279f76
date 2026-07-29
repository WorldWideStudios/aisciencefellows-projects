from execution.execution_functions import (
    move_arm_js,
    set_gripper,
    print_log,
)

# Eleven captured poses, replayed 1:1 in the order given.
# Driven joint-space (move_arm_js) so IK never re-solves and the TCP readout is
# irrelevant. Gripper widths are metres: each arm's raw reading normalised onto
# the shared 0-850 full-scale, then /10000 (850 units = 0.085 m).
#   right raw 678 -> 0.0678 (open) | 319 -> 0.0319 (closed on plate)
#   left  raw 81/84 -> 820/850 -> 0.0820 (open) | 76/84 -> 769/850 -> 0.0769 (closed)
WAYPOINTS = [
    # arm,         joint_angles,                                              width_m, note
    ("right_arm", [-0.536, 0.446, -0.886, -2.091, 1.376, 2.736],  0.0678, "R1 approach"),
    ("right_arm", [-0.536, 0.446, -0.886, -2.091, 1.376, 2.736],  0.0319, "R2 grasp"),
    ("right_arm", [0.129, 0.056, -0.408, -4.620, 1.534, 3.468],   0.0319, "R3 transit"),
    ("right_arm", [0.070, 0.343, -0.427, -4.618, 1.583, 3.233],   0.0319, "R4 place"),
    ("right_arm", [0.070, 0.343, -0.427, -4.618, 1.583, 3.233],   0.0678, "R5 release"),
    ("right_arm", [-0.026, -0.692, -0.599, -6.249, 1.282, 4.684], 0.0678, "R6 retreat"),

    ("left_arm",  [-0.172, 0.358, -0.499, -1.721, 1.509, -0.133], 0.0820, "L7 approach"),
    ("left_arm",  [-0.172, 0.358, -0.499, -1.721, 1.509, -0.133], 0.0769, "L8 grasp"),
    ("left_arm",  [-3.023, 0.040, -0.118, -3.028, 1.463, -0.071], 0.0769, "L9 transit"),
    ("left_arm",  [-3.023, 0.040, -0.118, -3.028, 1.463, -0.071], 0.0820, "L10 release"),
    ("left_arm",  [-3.086, -0.750, -0.515, -3.027, 0.347, -0.107], 0.0820, "L11 retreat"),
]


def waypoint_replay(speed: float = 0.15):
    """Replay the eleven captured arm poses in order (right arm, then left).

    Args:
        speed: Joint-space move speed as a fraction of max (0-1). Keep it low
            (~0.15) for the first real run so there's time to hit stop.
    """
    if not 0.0 < speed <= 1.0:
        raise ValueError("speed must be in (0, 1]")

    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Replaying {len(WAYPOINTS)} waypoints at speed={speed}")

    for i, (arm, joints, width_m, note) in enumerate(WAYPOINTS, start=1):
        print_log(f"[{i}/{len(WAYPOINTS)}] {note}: {arm} -> joints, gripper {width_m:.4f} m")
        move_arm_js(arm=arm, joint_angles=joints, speed=speed)
        set_gripper(arm, width_m)

    print_log("Waypoint replay complete")
    return {"success": True, "waypoints": len(WAYPOINTS)}
