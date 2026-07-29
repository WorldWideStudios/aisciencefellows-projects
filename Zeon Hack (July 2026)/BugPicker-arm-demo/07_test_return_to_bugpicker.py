#!/usr/bin/env python3
import time
from arm_common import (connect_arm, move_linear, release, payload, pause,
                        shutdown, TRANSIT_SAFE_POSE, IMAGER_PICKUP_APPROACH_POSE,
                        BUGPICKER_RETURN_APPROACH_POSE, BUGPICKER_RETURN_POSE,
                        PAYLOAD_EMPTY, PAYLOAD_LOADED, PRE_RELEASE_DWELL,
                        POST_RELEASE_DWELL)

arm = connect_arm()
try:
    print("Starting pose above imager:", IMAGER_PICKUP_APPROACH_POSE)
    print("BugPicker return approach:", BUGPICKER_RETURN_APPROACH_POSE)
    print("BugPicker return placement pose:", BUGPICKER_RETURN_POSE)
    pause("Return-leg test assumes the plate is already gripped above the imager. Confirm the plate is held and workspace is clear.")
    payload(arm, PAYLOAD_LOADED)
    bugpicker_high = list(BUGPICKER_RETURN_APPROACH_POSE)
    bugpicker_high[2] = TRANSIT_SAFE_POSE[2]
    move_linear(arm, "imager_pickup_approach", IMAGER_PICKUP_APPROACH_POSE, carrying=True)
    pause("At starting pose above imager with plate gripped. Continue to transit_safe?")
    move_linear(arm, "transit_safe", TRANSIT_SAFE_POSE, carrying=True)
    pause("At transit_safe. Continue to high pose above BugPicker?")
    move_linear(arm, "bugpicker_high", bugpicker_high, carrying=True)
    pause("At bugpicker_high. Continue down to BugPicker approach?")
    move_linear(arm, "bugpicker_approach", BUGPICKER_RETURN_APPROACH_POSE, carrying=True)
    pause("Check BugPicker alignment before descending to return the plate.")
    move_linear(arm, "bugpicker_place", BUGPICKER_RETURN_POSE, carrying=True)
    print(f"    settling before release... {PRE_RELEASE_DWELL}s")
    time.sleep(PRE_RELEASE_DWELL)
    release(arm)
    print(f"    holding after release... {POST_RELEASE_DWELL}s")
    time.sleep(POST_RELEASE_DWELL)
    payload(arm, PAYLOAD_EMPTY)
    pause("Released at BugPicker. Check placement before retracting.")
    move_linear(arm, "bugpicker_approach", BUGPICKER_RETURN_APPROACH_POSE)
finally:
    shutdown(arm)
