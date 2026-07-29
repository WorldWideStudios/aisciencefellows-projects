#!/usr/bin/env python3
from arm_common import (connect_arm, move_linear, release, grip, payload,
                        pause, shutdown, HOME_TRAVEL_POSE, PICKUP_APPROACH_POSE,
                        PICKUP_GRIP_POSE, PAYLOAD_EMPTY, PAYLOAD_LOADED)

arm = connect_arm()
try:
    print("Pickup approach:", PICKUP_APPROACH_POSE)
    print("Pickup grip:", PICKUP_GRIP_POSE)
    pause("This tests only the vertical pickup motion. Start near a safe clear pose.")
    release(arm)
    payload(arm, PAYLOAD_EMPTY)
    pickup_high = list(PICKUP_APPROACH_POSE)
    pickup_high[2] = HOME_TRAVEL_POSE[2]
    move_linear(arm, "home_travel", HOME_TRAVEL_POSE)
    pause("At home_travel. Continue to high pose above pickup XY?")
    move_linear(arm, "pickup_high", pickup_high)
    pause("At pickup_high. Continue down to pickup approach?")
    move_linear(arm, "pickup_approach", PICKUP_APPROACH_POSE)
    pause("At pickup approach, 50 mm above grip pose. Check alignment over the plate.")
    move_linear(arm, "pickup_grip", PICKUP_GRIP_POSE)
    pause("At pickup grip pose. Check gripper height before closing.")
    grip(arm)
    payload(arm, PAYLOAD_LOADED)
    pause("Gripper closed. Did it grip the plate correctly?")
    move_linear(arm, "pickup_approach", PICKUP_APPROACH_POSE, carrying=True)
finally:
    shutdown(arm)
