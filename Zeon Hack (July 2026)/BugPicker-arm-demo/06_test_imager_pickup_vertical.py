#!/usr/bin/env python3
from arm_common import (connect_arm, move_linear, release, grip, payload, pause,
                        shutdown, IMAGER_PICKUP_APPROACH_POSE,
                        IMAGER_PICKUP_POSE, PAYLOAD_EMPTY, PAYLOAD_LOADED)

arm = connect_arm()
try:
    print("Imager pickup approach:", IMAGER_PICKUP_APPROACH_POSE)
    print("Imager pickup pose:", IMAGER_PICKUP_POSE)
    pause("This tests only gripping/lifting the plate from the imager. Start near a safe clear pose.")
    release(arm)
    payload(arm, PAYLOAD_EMPTY)
    move_linear(arm, "imager_pickup_approach", IMAGER_PICKUP_APPROACH_POSE)
    pause("At imager pickup approach, 50 mm above pickup pose. Check alignment over the plate.")
    move_linear(arm, "imager_pickup", IMAGER_PICKUP_POSE)
    pause("At imager pickup pose. Check gripper height before closing.")
    grip(arm)
    payload(arm, PAYLOAD_LOADED)
    pause("Gripper closed. Did it grip the plate correctly?")
    move_linear(arm, "imager_pickup_approach", IMAGER_PICKUP_APPROACH_POSE, carrying=True)
finally:
    shutdown(arm)
