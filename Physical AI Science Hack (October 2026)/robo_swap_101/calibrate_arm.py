"""Run LeRobot calibration without the connection-time torque enable step."""
import sys
from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig
role = sys.argv[1]
if role == 'follower':
    arm = SO101Follower(SO101FollowerConfig(port='/dev/cu.usbmodem5A7A0547771', id='so101_follower_5A7A054777'))
elif role == 'leader':
    arm = SO101Leader(SO101LeaderConfig(port='/dev/cu.usbmodem5A680086601', id='so101_leader_5A68008660'))
else:
    raise ValueError(role)
try:
    arm.bus.connect()
    arm.bus.disable_torque(num_retry=3)
    arm.calibrate()
finally:
    if arm.bus.is_connected:
        arm.bus.disconnect()
