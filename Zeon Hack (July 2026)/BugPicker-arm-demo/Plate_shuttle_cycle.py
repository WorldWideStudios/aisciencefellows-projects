#!/usr/bin/env python3
"""
xArm 7 plate shuttle - one cycle.

Sequence (as taught):
    home_travel -> pickup_approach -> grasp -> lift
    -> [safe transit] -> place_approach -> place -> wait (imaging)
    -> place_approach -> place -> place_approach
    -> lift -> [safe transit] -> grasp -> pickup_approach -> travel

Function: lift a 96-well plate off the BugPicker, set it on the imager,
hold while it images, then pick it back up and return it to the BugPicker.

Long travel motions are JOINT moves (set_servo_angle). Near the plate, the
script uses Cartesian straight-line moves so approach/retract motions are
50 mm directly above the pickup/drop positions.

Requires: xArm-Python-SDK  ->  pip install xArm-Python-SDK
"""

import subprocess
import sys
import time
from xarm.wrapper import XArmAPI

# ============================================================================
# CONFIG  -- edit this block, then run
# ============================================================================

ARM_IP = "192.168.1.209"          # controller IP

# ---- Speeds (deg/s or mm/s) and accel (deg/s^2 or mm/s^2). 1.5x previous values. ----
SPEED_NORMAL = 30                 # empty-gripper joint moves
SPEED_CARRY  = 15                 # joint moves while holding the plate
SPEED_LINEAR = 50                 # Cartesian near-plate moves
ACCEL        = 225
LINEAR_ACCEL = 225

# ---- Cartesian approach height ----
APPROACH_Z_OFFSET_MM = 50.0

# ---- Gripper (xArm Gripper, 0 = closed ... 850 = open) ----
GRIP    = 755                     # clamp onto plate
RELEASE = 850                     # open to release
GRIPPER_CLOSE_SPEED = 2000
GRIPPER_OPEN_SPEED = 500
DWELL   = 1.0                     # seconds to settle after each grip/release
PRE_RELEASE_DWELL = 2.0
POST_RELEASE_DWELL = 2.0             # seconds to hold after release before retracting

# ---- Imaging hold ----
IMAGING_WAIT = 5.0                # fallback seconds parked at the wait pose
PLATE_READER_SCAN = [sys.executable, "/home/biokea-06/Documents/PlateReader/scan96.py"]

# ---- TCP payload  [weight_kg, [Cx, Cy, Cz] mm]  (PLACEHOLDERS - measure these) ----
PAYLOAD_EMPTY  = [0.0, [0.0, 0.0, 0.0]]      # gripper only (set real values)
PAYLOAD_LOADED = [0.0, [0.0, 0.0, 0.0]]      # gripper + plate (set real values)

# ---- Taught Cartesian intermediate poses: [x, y, z, roll, pitch, yaw]
HOME_TRAVEL_POSE = [-323.507568, 254.225876, 424.773499, 178.134068, -0.631285, 89.679812]
FINAL_TRAVEL_POSE = [-323.507568, 254.225876, 526.373499, 178.134068, -0.631285, 89.679812]
TRANSIT_SAFE_POSE = [-79.206612, 373.046295, 424.773346, 178.16432, -0.660219, 89.678323]
WAIT_POSE = [172.5457, 365.435822, 270.98172, 178.167644, -0.651739, 89.675515]

# ---- Taught Cartesian TCP poses: [x, y, z, roll, pitch, yaw]
# Units are mm/degrees. The approach poses are calculated as 50 mm directly
# above these positions. Orientation is set to straight down for Cartesian moves.
TOOL_DOWN_RPY    = [180.0, 0.0, -180.0]
PICKUP_GRIP_POSE   = [-395.2, 311.5, 235.4, 179.6, -3.8, 89.3]
BUGPICKER_RETURN_POSE = [-393.2, 306.5, 243.0, 179.5, -3.7, 89.3]
IMAGER_PLACE_POSE  = [184.5, 364.9, 167.8, 179.2, -5.3, 89.3]
IMAGER_PICKUP_POSE = [186.4, 360.7, 164.8, 179.1, -6.0, 89.2]


# ============================================================================
# INTERNALS
# ============================================================================

def preflight():
    problems = []
    if TRANSIT_SAFE_POSE is None:
        problems.append("TRANSIT_SAFE_POSE is not set. Record a safe high pose first.")
    if ARM_IP.endswith("xxx"):
        problems.append("ARM_IP is still the placeholder.")
    if PICKUP_GRIP_POSE is None:
        problems.append("PICKUP_GRIP_POSE is not set. Record the Cartesian grip pose first.")
    if BUGPICKER_RETURN_POSE is None:
        problems.append("BUGPICKER_RETURN_POSE is not set. Record the Cartesian BugPicker return pose first.")
    if IMAGER_PLACE_POSE is None:
        problems.append("IMAGER_PLACE_POSE is not set. Record the Cartesian imager place pose first.")
    if IMAGER_PICKUP_POSE is None:
        problems.append("IMAGER_PICKUP_POSE is not set. Record the Cartesian imager pickup pose first.")
    if PAYLOAD_LOADED[0] == 0.0:
        print("[warn] PAYLOAD_LOADED is still 0 kg - the arm's gravity model will")
        print("       be wrong while carrying. OK for slow first runs, fix before speed.")
    if problems:
        for p in problems:
            print(f"[abort] {p}")
        sys.exit(1)


def check(code, label):
    if code != 0:
        print(f"[ERROR] {label} -> code {code}. Stopping.")
        shutdown()
        sys.exit(1)


def check_motion(code, label, retry_func=None):
    if code == 0:
        return
    if code == -9 and retry_func is not None:
        print(f"[warn] {label} stopped with code -9. Clearing state and retrying once.")
        time.sleep(1.0)
        ready()
        retry_code = retry_func()
        if retry_code == 0:
            print(f"[warn] {label} retry succeeded.")
            return
        code = retry_code
    print(f"[ERROR] {label} -> code {code}. Stopping.")
    shutdown()
    sys.exit(1)


def ready():
    arm.clean_warn()
    arm.clean_error()
    check(arm.motion_enable(True), "motion enable")
    check(arm.set_mode(0), "set position mode")
    check(arm.set_state(0), "set ready state")
    time.sleep(0.2)


def move(name, angle, carrying=False):
    ready()
    spd = SPEED_CARRY if carrying else SPEED_NORMAL
    tag = " [carrying]" if carrying else ""
    print(f" -> {name} @ {spd} deg/s{tag}")
    def command():
        return arm.set_servo_angle(angle=angle, speed=spd, mvacc=ACCEL,
                                   wait=True, is_radian=False)
    check_motion(command(), f"move {name}", command)


def approach_pose(pose):
    above = list(pose)
    above[2] += APPROACH_Z_OFFSET_MM
    return above


def move_linear(name, pose, carrying=False):
    ready()
    tag = " [carrying]" if carrying else ""
    print(f" -> {name} @ {SPEED_LINEAR} mm/s{tag}: {pose}")
    def command():
        return arm.set_position(*pose, speed=SPEED_LINEAR, mvacc=LINEAR_ACCEL,
                                wait=True, is_radian=False)
    check_motion(command(), f"linear move {name}", command)


def grip():
    ready()
    print(f"    gripper CLOSE ({GRIP}) @ speed {GRIPPER_CLOSE_SPEED}")
    check(arm.set_gripper_speed(GRIPPER_CLOSE_SPEED), "set gripper close speed")
    check(arm.set_gripper_position(GRIP, wait=True), "gripper close")
    time.sleep(DWELL)


def release():
    ready()
    print(f"    gripper OPEN ({RELEASE}) @ speed {GRIPPER_OPEN_SPEED}")
    check(arm.set_gripper_speed(GRIPPER_OPEN_SPEED), "set gripper open speed")
    check(arm.set_gripper_position(RELEASE, wait=True), "gripper open")
    time.sleep(DWELL)


def payload(p):
    check(arm.set_tcp_load(p[0], p[1]), "set tcp load")


def run_plate_reader_scan():
    print(f"    running plate reader scan: {' '.join(PLATE_READER_SCAN)}")
    result = subprocess.run(PLATE_READER_SCAN, check=False)
    if result.returncode != 0:
        print(f"[ERROR] plate reader scan failed -> code {result.returncode}. Stopping.")
        shutdown()
        sys.exit(result.returncode)


def shutdown():
    try:
        arm.disconnect()
    except Exception:
        pass


# ============================================================================
# MAIN
# ============================================================================

preflight()

arm = XArmAPI(ARM_IP, is_radian=False)
arm.clean_warn()
arm.clean_error()
check(arm.motion_enable(True), "motion enable")
check(arm.set_mode(0), "set position mode")
check(arm.set_state(0), "set ready state")
check(arm.set_gripper_mode(0), "set gripper mode")
check(arm.set_gripper_enable(True), "enable gripper")
check(arm.set_gripper_speed(GRIPPER_CLOSE_SPEED), "set gripper speed")

pickup_approach = approach_pose(PICKUP_GRIP_POSE)
bugpicker_return_approach = approach_pose(BUGPICKER_RETURN_POSE)
imager_place_approach = approach_pose(IMAGER_PLACE_POSE)
imager_pickup_approach = approach_pose(IMAGER_PICKUP_POSE)

pickup_high = list(pickup_approach)
pickup_high[2] = TRANSIT_SAFE_POSE[2]
bugpicker_return_high = list(bugpicker_return_approach)
bugpicker_return_high[2] = TRANSIT_SAFE_POSE[2]

input("Arm enabled. Clear the workspace, then press Enter to start the cycle...")

try:
    # ---- Forward: BugPicker -> imager ----
    release()                                 # start open, empty
    payload(PAYLOAD_EMPTY)
    move_linear("home_travel", HOME_TRAVEL_POSE)
    move_linear("pickup_high", pickup_high)
    move_linear("pickup_approach", pickup_approach)
    move_linear("pickup_grip", PICKUP_GRIP_POSE)
    grip()
    payload(PAYLOAD_LOADED)
    move_linear("pickup_approach", pickup_approach, carrying=True)
    move_linear("transit_safe", TRANSIT_SAFE_POSE, carrying=True)
    move_linear("imager_place_approach", imager_place_approach, carrying=True)
    move_linear("imager_place", IMAGER_PLACE_POSE, carrying=True)
    print(f"    settling before release... {PRE_RELEASE_DWELL}s")
    time.sleep(PRE_RELEASE_DWELL)
    release()
    print(f"    holding after release... {POST_RELEASE_DWELL}s")
    time.sleep(POST_RELEASE_DWELL)
    payload(PAYLOAD_EMPTY)
    move_linear("imager_place_approach", imager_place_approach)

    # ---- Imaging hold ----
    move_linear("wait", WAIT_POSE)
    run_plate_reader_scan()

    # ---- Return: imager -> BugPicker ----
    move_linear("imager_pickup_approach", imager_pickup_approach)
    move_linear("imager_pickup", IMAGER_PICKUP_POSE)
    grip()
    payload(PAYLOAD_LOADED)
    move_linear("imager_pickup_approach", imager_pickup_approach, carrying=True)
    move_linear("transit_safe", TRANSIT_SAFE_POSE, carrying=True)
    move_linear("bugpicker_return_high", bugpicker_return_high, carrying=True)
    move_linear("bugpicker_return_approach", bugpicker_return_approach, carrying=True)
    move_linear("bugpicker_return", BUGPICKER_RETURN_POSE, carrying=True)
    print(f"    settling before release... {PRE_RELEASE_DWELL}s")
    time.sleep(PRE_RELEASE_DWELL)
    release()
    print(f"    holding after release... {POST_RELEASE_DWELL}s")
    time.sleep(POST_RELEASE_DWELL)
    payload(PAYLOAD_EMPTY)
    move_linear("bugpicker_return_approach", bugpicker_return_approach)
    move_linear("home_travel", HOME_TRAVEL_POSE)

    print("Cycle complete.")

except KeyboardInterrupt:
    print("\nInterrupted by user.")
finally:
    shutdown()