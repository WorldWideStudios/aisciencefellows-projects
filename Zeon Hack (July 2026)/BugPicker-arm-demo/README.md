# BugPicker Arm Plate Shuttle

This folder contains the xArm 7 plate-shuttling workflow for moving a 96-well plate between the BugPicker and the imager/plate-reader station.

The main script, `Plate_shuttle_cycle.py`, performs one complete automated cycle:

1. Open gripper and move to the BugPicker start area.
2. Pick up the 96-well plate from the BugPicker.
3. Transfer the plate to the imager.
4. Release the plate and move to the imaging wait pose.
5. Run the plate-reader scan script: `/home/biokea-06/Documents/PlateReader/scan96.py`.
6. Pick the plate back up from the imager.
7. Return and release the plate onto the BugPicker.
8. Retract and return to the home travel pose.

## Project Context

This workflow was built as part of the [AI Science World Model Hack Hub Zeon Systems](https://app.notion.com/p/AI-Science-World-Model-Hack-Hub-Zeon-Systems-389ee7a4c4578088bd99c7b454c20491) hackathon.

The goal was to demonstrate how AI-assisted software development and robotics can automate a real biological discovery bottleneck: moving 96-well plates between organism-handling, imaging, and scanning stations.

## Hardware

- uFactory xArm 7
- xArm gripper
- BugPicker station
- Imager / plate-reader station
- 96-well plate workflow

## Software Requirements

Use the Python virtual environment that has the xArm SDK and plate-reader dependencies installed:

```bash
source ~/Documents/xarm-venv/bin/activate
```

The main script imports `xarm.wrapper.XArmAPI` and runs the plate-reader script with the same Python executable:

```python
PLATE_READER_SCAN = [sys.executable, "/home/biokea-06/Documents/PlateReader/scan96.py"]
```

## Running the Full Cycle

From this folder:

```bash
cd ~/Documents/BugPicker_arm
source ~/Documents/xarm-venv/bin/activate
python Plate_shuttle_cycle.py
```

The script pauses before motion:

```text
Arm enabled. Clear the workspace, then press Enter to start the cycle...
```

Only press Enter after the workspace is clear and the plate/fixtures are ready.

## Current Key Settings

Robot controller IP:

```python
ARM_IP = "192.168.1.209"
```

Motion speeds:

```python
SPEED_LINEAR = 50
SPEED_NORMAL = 30
SPEED_CARRY = 15
```

Gripper settings:

```python
GRIP = 755
RELEASE = 850
GRIPPER_CLOSE_SPEED = 2000
GRIPPER_OPEN_SPEED = 500
```

Release timing:

```python
PRE_RELEASE_DWELL = 2.0
POST_RELEASE_DWELL = 2.0
```

Approach height:

```python
APPROACH_Z_OFFSET_MM = 50.0
```

## Safety Notes

- Keep a hand near the emergency stop during tests and demos.
- Do not open the gripper manually or in software while the plate is unsupported.
- The script includes a one-time retry for motion stop error `-9`. It clears state and retries the same motion once without changing the gripper state.
- If a retried move also fails, the script stops.
- Payload values are still placeholders. Update `PAYLOAD_EMPTY` and `PAYLOAD_LOADED` before increasing speed or running extended unattended cycles.

## Motion Recovery Behavior

`Plate_shuttle_cycle.py` includes `check_motion(...)`, which handles intermittent xArm stop-state motion failures:

```text
motion returns code -9
clear warning/error
set arm ready
retry the same motion once
continue if retry succeeds
stop if retry fails
```

This was added because the carried move into `transit_safe` occasionally entered `state=4`, while a cleared retry succeeded.

## Test Scripts

Use these scripts to test individual sections instead of running the full cycle.

```text
00_read_current_pose.py              Print current TCP pose and joint angles.
01_test_gripper.py                   Test gripper open/close.
02_test_pickup_vertical.py           Test BugPicker pickup approach, grip, and lift.
03_test_drop_vertical.py             Test placing the plate onto the imager.
04_test_transit.py                   Test home/transit/wait movement poses.
05_test_forward_no_return.py         Test BugPicker -> imager only.
06_test_imager_pickup_vertical.py    Test pickup from the imager.
07_test_return_to_bugpicker.py       Test imager -> BugPicker return.
08_record_intermediate_pose.py       Record new taught poses from the current arm position.
```

Run a test script like this:

```bash
cd ~/Documents/BugPicker_arm
source ~/Documents/xarm-venv/bin/activate
python 02_test_pickup_vertical.py
```

## Important Poses

The main workflow uses Cartesian poses in the form:

```python
[x, y, z, roll, pitch, yaw]
```

Units:

```text
x/y/z = mm
roll/pitch/yaw = degrees
```

Current primary poses are defined in `Plate_shuttle_cycle.py` and mirrored in `arm_common.py` for the test scripts.

## Slide Deck

A short project deck is also in this folder:

```text
BugPicker_biodiversity_robotics_deck.pptx
```

It summarizes the project idea, hypothesis, demo, impact, and next steps.
