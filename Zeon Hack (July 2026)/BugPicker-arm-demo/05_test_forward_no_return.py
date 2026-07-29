#!/usr/bin/env python3
import time
from arm_common import (connect_arm, move_linear, release, grip,
                        payload, pause, shutdown, HOME_TRAVEL_POSE, TRANSIT_SAFE_POSE,
                        PICKUP_APPROACH_POSE, PICKUP_GRIP_POSE,
                        DROP_APPROACH_POSE, DROP_POSE,
                        PAYLOAD_EMPTY, PAYLOAD_LOADED, PRE_RELEASE_DWELL, POST_RELEASE_DWELL)

arm = connect_arm()
try:
    pause("Forward-only test: pickup, transit, drop. Keep workspace clear.")
    release(arm)
    print(f"    holding after release... {POST_RELEASE_DWELL}s")
    time.sleep(POST_RELEASE_DWELL)
    payload(arm, PAYLOAD_EMPTY)
    move_linear(arm, "home_travel", HOME_TRAVEL_POSE)
    move_linear(arm, "pickup_approach", PICKUP_APPROACH_POSE)
    pause("Check pickup alignment before descending.")
    move_linear(arm, "pickup_grip", PICKUP_GRIP_POSE)
    grip(arm)
    payload(arm, PAYLOAD_LOADED)
    pause("Check plate grip before lifting.")
    move_linear(arm, "pickup_approach", PICKUP_APPROACH_POSE, carrying=True)
    move_linear(arm, "transit_safe", TRANSIT_SAFE_POSE, carrying=True)
    move_linear(arm, "drop_approach", DROP_APPROACH_POSE, carrying=True)
    pause("Check drop alignment before descending.")
    move_linear(arm, "drop", DROP_POSE, carrying=True)
    print(f"    settling before release... {PRE_RELEASE_DWELL}s")
    time.sleep(PRE_RELEASE_DWELL)
    release(arm)
    print(f"    holding after release... {POST_RELEASE_DWELL}s")
    time.sleep(POST_RELEASE_DWELL)
    payload(arm, PAYLOAD_EMPTY)
    move_linear(arm, "drop_approach", DROP_APPROACH_POSE)
finally:
    shutdown(arm)
