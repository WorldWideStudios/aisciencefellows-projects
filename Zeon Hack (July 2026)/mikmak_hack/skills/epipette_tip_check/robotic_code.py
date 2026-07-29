from datetime import datetime, timezone
import time

from laser_read.robotic_code import laser_read

from .modules import (
    get_arm_pose,
    move_arm,
    move_arm_js,
    move_relative,
    print_log,
)

# TODO: replace with the real joint angles for the tip-check pose (6 values, radians)
TIP_CHECK_JOINTS = [-0.210, -0.680, -0.864, -0.026, 1.607, 4.496]

# Cartesian pose of the arm when sitting at TIP_CHECK_JOINTS.
# Position is used to compute the 15 cm approach height; orientation is used
# for the Cartesian approach move so the wrist is already aligned.
# Captured TCP at reading pose: [0.562, -0.007, 0.169, -2.672, -1.482, -0.464]
TIP_CHECK_TCP = [0.562, -0.007, 0.169]
ARM_ORIENTATION = [-2.672, -1.482, -0.464]

PRE_TIP_CHECK_JOINTS = [0.893, 0.354, -1.207, -0.881, 2.177, 2.538]

APPROACH_M = 0.15  # 15 cm above the reading pose
SETTLE_S = 2.0     # let the arm settle before sampling the laser

# Skill-side tip-presence rule (ignore the firmware's persisted threshold).
# Compared against the *sum* of laser_read's 3 samples, not each sample individually.
TIP_PRESENT_THRESHOLD = 10000    # raw ADC counts (sum of 3 readings)
TIP_PRESENT_DIRECTION = "above"  # "above" -> tip_present when sample_sum > threshold


def epipette_tip_check():
    """Side-trip the left arm to the laser to verify a tip is attached.

    Sequence:
      1. capture start (pipetting) pose
      2. Cartesian approach to 15 cm above the reading pose (ARM_ORIENTATION)
      3. joint move to TIP_CHECK_JOINTS (the reading pose)
      4. settle SETTLE_S seconds
      5. read laser (3 samples); tip_present = sum(samples) > TIP_PRESENT_THRESHOLD
      6. retreat 15 cm up
      7. Cartesian return to the start pose

    Steps 4–7 are wrapped in try/finally so the arm retraces even if
    laser_read raises.
    """
    print_log(runlog=True, runlog_type="step_start")
    step_start = datetime.now(timezone.utc)
    start_pose = get_arm_pose("left_arm")  # [x, y, z, roll, pitch, yaw]
    print_log(f"epipette_tip_check: start pose = {start_pose.tolist()}")

    move_arm_js(arm="left_arm", joint_angles=PRE_TIP_CHECK_JOINTS, speed=0.5)
    
    move_arm(
        arm="left_arm",
        position=[TIP_CHECK_TCP[0], TIP_CHECK_TCP[1], TIP_CHECK_TCP[2] + APPROACH_M],
        orientation=ARM_ORIENTATION,
        speed=100,
    )
    # move_arm_js(arm="left_arm", joint_angles=TIP_CHECK_JOINTS, speed=0.5)
    move_arm(
        arm="left_arm",
        position=[TIP_CHECK_TCP[0], TIP_CHECK_TCP[1], TIP_CHECK_TCP[2]],
        orientation=ARM_ORIENTATION,
        speed=100,
    )

    reading = None
    samples = None
    sample_sum = None
    tip_present = False
    try:
        time.sleep(SETTLE_S)
        reading = laser_read()
        samples = reading["values"]
        sample_sum = sum(samples)
        tip_present = (
            (sample_sum > TIP_PRESENT_THRESHOLD)
            if TIP_PRESENT_DIRECTION == "above"
            else (sample_sum < TIP_PRESENT_THRESHOLD)
        )
        print_log(
            f"epipette_tip_check: samples={samples} sum={sample_sum} "
            f"threshold={TIP_PRESENT_THRESHOLD} tip_present={tip_present}",
        )
        _elapsed = (datetime.now(timezone.utc) - step_start).total_seconds()
        print_log(
            (f"[+{_elapsed:.1f}s] Tip detected on pipette." if tip_present
             else f"[+{_elapsed:.1f}s] No tip detected on pipette."),
            runlog=True, runlog_type="event",
        )
    finally:
        move_relative(arm="left_arm", delta_xyz=[0.0, 0.0, +APPROACH_M], speed=100)
        move_arm_js(arm="left_arm", joint_angles=PRE_TIP_CHECK_JOINTS, speed=0.5)
        
    return {
        "success": True,
        "tip_present": tip_present,
        "value": sample_sum if reading else None,
        "values": samples if reading else None,
        "threshold": TIP_PRESENT_THRESHOLD,
        "direction": TIP_PRESENT_DIRECTION,
        "laser": reading,
    }
