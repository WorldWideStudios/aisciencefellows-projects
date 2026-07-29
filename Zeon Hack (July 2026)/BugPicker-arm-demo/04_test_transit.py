#!/usr/bin/env python3
from arm_common import (connect_arm, move_linear, pause, shutdown,
                        HOME_TRAVEL_POSE, TRANSIT_SAFE_POSE, WAIT_POSE)

arm = connect_arm()
try:
    pause("This tests only the joint-space travel poses with no plate.")
    move_linear(arm, "home_travel", HOME_TRAVEL_POSE)
    pause("At home_travel. Continue to transit_safe?")
    move_linear(arm, "transit_safe", TRANSIT_SAFE_POSE)
    pause("At transit_safe. Continue to wait pose?")
    move_linear(arm, "wait", WAIT_POSE)
finally:
    shutdown(arm)
