#!/usr/bin/env python3
from arm_common import connect_arm, release, grip, pause, shutdown

arm = connect_arm()
try:
    pause("Testing gripper open/close. Keep clear of the gripper.")
    release(arm)
    pause("Gripper opened.")
    grip(arm)
    pause("Gripper closed.")
    release(arm)
finally:
    shutdown(arm)
