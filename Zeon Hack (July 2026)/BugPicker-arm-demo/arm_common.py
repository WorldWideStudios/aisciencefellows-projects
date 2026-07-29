#!/usr/bin/env python3
"""Shared xArm helpers and positions for BugPicker plate-shuttle tests."""

import sys
import time
from xarm.wrapper import XArmAPI

ARM_IP = "192.168.1.209"

SPEED_NORMAL = 30
SPEED_CARRY = 15
SPEED_LINEAR = 50
ACCEL = 225
LINEAR_ACCEL = 225

APPROACH_Z_OFFSET_MM = 50.0

GRIP = 755
RELEASE = 850
GRIPPER_CLOSE_SPEED = 2000
GRIPPER_OPEN_SPEED = 500
DWELL = 1.0
PRE_RELEASE_DWELL = 2.0
POST_RELEASE_DWELL = 2.0

PAYLOAD_EMPTY = [0.0, [0.0, 0.0, 0.0]]
PAYLOAD_LOADED = [0.0, [0.0, 0.0, 0.0]]

HOME_TRAVEL_POSE = [-323.507568, 254.225876, 424.773499, 178.134068, -0.631285, 89.679812]
FINAL_TRAVEL_POSE = [-323.507568, 254.225876, 526.373499, 178.134068, -0.631285, 89.679812]
TRANSIT_SAFE_POSE = [-79.206612, 373.046295, 424.773346, 178.16432, -0.660219, 89.678323]
WAIT_POSE = [172.5457, 365.435822, 270.98172, 178.167644, -0.651739, 89.675515]

# Legacy joint waypoints retained only for reference.
HOME_TRAVEL = [65.6, 44.4, 124.4, 93.5, -41.1, 114.7, 0.0]
WAIT = [-52.8, 22.0, 140.9, 64.5, -11.1, 81.6, -89.5]
TRANSIT_SAFE = [-47.7, 29.3, 168.2, 94.8, -6.4, 122.5, -61.8]

TOOL_DOWN_RPY = [180.0, 0.0, -180.0]

PICKUP_GRIP_POSE = [-395.2, 311.5, 235.4, 179.6, -3.8, 89.3]
BUGPICKER_RETURN_POSE = [-393.2, 306.5, 243.0, 179.5, -3.7, 89.3]
IMAGER_PLACE_POSE = [184.5, 364.9, 167.8, 179.2, -5.3, 89.3]
IMAGER_PICKUP_POSE = [186.4, 360.7, 164.8, 179.1, -6.0, 89.2]


def approach_pose(pose):
    above = list(pose)
    above[2] += APPROACH_Z_OFFSET_MM
    return above


PICKUP_APPROACH_POSE = approach_pose(PICKUP_GRIP_POSE)
BUGPICKER_RETURN_APPROACH_POSE = approach_pose(BUGPICKER_RETURN_POSE)
IMAGER_PLACE_APPROACH_POSE = approach_pose(IMAGER_PLACE_POSE)
IMAGER_PICKUP_APPROACH_POSE = approach_pose(IMAGER_PICKUP_POSE)

# Backwards-compatible names for drop-testing the forward placement step.
DROP_POSE = IMAGER_PLACE_POSE
DROP_APPROACH_POSE = IMAGER_PLACE_APPROACH_POSE


def check(code, label, arm=None):
    if code != 0:
        print(f"[ERROR] {label} -> code {code}. Stopping.")
        if arm is not None:
            shutdown(arm)
        sys.exit(1)


def connect_arm():
    arm = XArmAPI(ARM_IP, is_radian=False)
    arm.clean_warn()
    arm.clean_error()
    check(arm.motion_enable(True), "motion enable", arm)
    check(arm.set_mode(0), "set position mode", arm)
    check(arm.set_state(0), "set ready state", arm)
    check(arm.set_gripper_mode(0), "set gripper mode", arm)
    check(arm.set_gripper_enable(True), "enable gripper", arm)
    check(arm.set_gripper_speed(GRIPPER_CLOSE_SPEED), "set gripper speed", arm)
    return arm


def ready(arm):
    arm.clean_warn()
    arm.clean_error()
    check(arm.motion_enable(True), "motion enable", arm)
    check(arm.set_mode(0), "set position mode", arm)
    check(arm.set_state(0), "set ready state", arm)
    time.sleep(0.2)


def move_joint(arm, name, angle, carrying=False):
    ready(arm)
    spd = SPEED_CARRY if carrying else SPEED_NORMAL
    tag = " [carrying]" if carrying else ""
    print(f" -> {name} @ {spd} deg/s{tag}")
    check(arm.set_servo_angle(angle=angle, speed=spd, mvacc=ACCEL,
                              wait=True, is_radian=False), f"move {name}", arm)


def move_linear(arm, name, pose, carrying=False):
    ready(arm)
    tag = " [carrying]" if carrying else ""
    print(f" -> {name} @ {SPEED_LINEAR} mm/s{tag}: {pose}")
    check(arm.set_position(*pose, speed=SPEED_LINEAR, mvacc=LINEAR_ACCEL,
                           wait=True, is_radian=False), f"linear move {name}", arm)


def grip(arm):
    ready(arm)
    print(f"    gripper CLOSE ({GRIP}) @ speed {GRIPPER_CLOSE_SPEED}")
    check(arm.set_gripper_speed(GRIPPER_CLOSE_SPEED), "set gripper close speed", arm)
    check(arm.set_gripper_position(GRIP, wait=True), "gripper close", arm)
    time.sleep(DWELL)


def release(arm):
    ready(arm)
    print(f"    gripper OPEN ({RELEASE}) @ speed {GRIPPER_OPEN_SPEED}")
    check(arm.set_gripper_speed(GRIPPER_OPEN_SPEED), "set gripper open speed", arm)
    check(arm.set_gripper_position(RELEASE, wait=True), "gripper open", arm)
    time.sleep(DWELL)


def payload(arm, p):
    check(arm.set_tcp_load(p[0], p[1]), "set tcp load", arm)


def print_current_pose(arm):
    code, position = arm.get_position(is_radian=False)
    check(code, "get position", arm)
    code, angles = arm.get_servo_angle(is_radian=False)
    check(code, "get servo angles", arm)
    print(f"Current TCP pose [x, y, z, roll, pitch, yaw]: {position}")
    print(f"Current joints [J1..J7]: {angles}")


def pause(message):
    input(f"{message}\nPress Enter to continue, or Ctrl-C to stop...")


def shutdown(arm):
    try:
        arm.disconnect()
    except Exception:
        pass
