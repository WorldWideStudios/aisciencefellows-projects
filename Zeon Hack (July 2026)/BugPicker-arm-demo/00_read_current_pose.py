#!/usr/bin/env python3
from arm_common import connect_arm, print_current_pose, shutdown

arm = connect_arm()
try:
    print_current_pose(arm)
finally:
    shutdown(arm)
