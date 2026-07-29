#!/usr/bin/env python3
import time
from arm_common import (connect_arm, move_linear, release, grip, payload, pause,
                        shutdown, DROP_APPROACH_POSE, DROP_POSE,
                        PAYLOAD_EMPTY, PAYLOAD_LOADED, PRE_RELEASE_DWELL, POST_RELEASE_DWELL)

arm = connect_arm()
try:
    print("Drop approach:", DROP_APPROACH_POSE)
    print("Drop pose:", DROP_POSE)
    pause("This tests only the vertical drop motion. Start with or without a test plate as appropriate.")
    payload(arm, PAYLOAD_LOADED)
    move_linear(arm, "drop_approach", DROP_APPROACH_POSE, carrying=True)
    pause("At drop approach, 50 mm above drop pose. Check alignment over the target.")
    move_linear(arm, "drop", DROP_POSE, carrying=True)
    pause("At drop pose. Check placement height before release.")
    print(f"    settling before release... {PRE_RELEASE_DWELL}s")
    time.sleep(PRE_RELEASE_DWELL)
    release(arm)
    print(f"    holding after release... {POST_RELEASE_DWELL}s")
    time.sleep(POST_RELEASE_DWELL)
    payload(arm, PAYLOAD_EMPTY)
    pause("Released. Check whether the plate sits correctly.")
    move_linear(arm, "drop_approach", DROP_APPROACH_POSE)
finally:
    shutdown(arm)
