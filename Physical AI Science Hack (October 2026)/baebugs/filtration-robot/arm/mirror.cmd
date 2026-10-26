@echo off
rem Mirror the SO-101 follower (COM6) to the leader (COM5) with LeRobot.
echo Pose the LEADER roughly like the FOLLOWER and keep hands clear of the follower.
echo To stop: hold the follower, then press Ctrl+C (it goes limp).
pause
"%USERPROFILE%\lerobot-env\Scripts\lerobot-teleoperate.exe" --robot.type=so101_follower --robot.port=COM6 --robot.id=my_follower --teleop.type=so101_leader --teleop.port=COM5 --teleop.id=my_leader
