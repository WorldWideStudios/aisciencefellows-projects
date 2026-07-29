#!/usr/bin/env python3
"""Print the current xArm pose for copying into arm_common.py/Plate_shuttle_cycle.py.

Jog the arm in UFACTORY Studio to a safe intermediate pose with the gripper in
its desired 90-degree-rotated orientation, then run this script. It prints both
Cartesian TCP pose and joint angles. For HOME_TRAVEL, TRANSIT_SAFE, and WAIT we
currently use the joint-angle values.
"""

from arm_common import connect_arm, print_current_pose, pause, shutdown

arm = connect_arm()
try:
    pause("Jog the arm to the intermediate pose you want to record.")
    print_current_pose(arm)
finally:
    shutdown(arm)
