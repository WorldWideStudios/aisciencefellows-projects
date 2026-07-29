import time

from protocol_schema import SkillObject
from utils import object_display_name

from .modules import (
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    get_object_pose,
    get_world_state,
    move_arm,
    move_arm_js,
    print_log,
)

# Absolute world Z of the tip tops — same constant epipette_attach uses.
TIP_HEIGHT = 0.045

# Fixed nozzle-down orientation over the rack (left arm), shared with epipette_attach.
ARM_ORIENTATION = [-0.977, -1.555, -2.200]

# Staging joint pose over the tip rack (left arm).
ATTACH_JOINTS = [0.893, 0.354, -1.207, -0.881, 2.177, 2.538]


def epipette_attach_test(
    tipbox: SkillObject,
    pipette: SkillObject,
    num_tips: int = 96,
):
    """Loop over every tip running the epipette_attach motion, but never insert.

    Same targeting as epipette_attach (per-pipette calibration XY + stored tcp_offset
    + per-pipette attach_depths), but skips the press (step 2) and repeats the descend
    move in step 3, so the nozzle only hovers just above each tip top. Nothing is
    picked up and no world state is advanced — a calibration sweep to eyeball each tip.
    """
    print_log(runlog=True, runlog_type="step_start")
    tipbox_id = tipbox.id
    tipbox_name = object_display_name(tipbox)
    pipette_id = pipette.id
    pipette_name = object_display_name(pipette)

    calib_key = f"calibration_{pipette_name}"
    depths_key = f"attach_depths_{pipette_name}"
    print_log(
        f"Starting epipette_attach_test (tipbox={tipbox_name or tipbox_id}, pipette={pipette_name}, num_tips={num_tips})"
    )

    move_arm_js(arm="left_arm", joint_angles=ATTACH_JOINTS, speed=1)

    stored = get_world_state(pipette_id).get("tcp_offset")
    tcp_offset = [float(v) for v in stored] if (stored is not None and len(stored) == 3) else None

    tipbox_pose = get_object_pose(tipbox_name)
    calibration = get_world_state(tipbox_id).get(calib_key, {})
    attach_depths = get_world_state(tipbox_id).get(depths_key, [0.015, -0.002, -0.003, 0.15])
    orientation = compute_dispense_orientation(0, 0)

    for tip_index in range(1, num_tips + 1):
        dx, dy = calibration.get(str(tip_index), [0.0, 0.0])
        tip_target = [tipbox_pose["xyz"][0] + dx, tipbox_pose["xyz"][1] + dy, TIP_HEIGHT]

        tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(tip_target, orientation, tcp_offset=tcp_offset)
        x, y, ref_z = tcp_position[0], tcp_position[1], tcp_position[2]
        print_log(f"epipette_attach_test: tip {tip_index}/{num_tips} target {tip_target} -> TCP z {ref_z} (dx={dx}, dy={dy})")

        # depths[0] descend, depths[1] press, then depths[3] lift (skip depths[2]).
        move_arm(arm="left_arm", position=[x, y, ref_z + 0.005], orientation=ARM_ORIENTATION, speed=250)

        move_arm(arm="left_arm", position=[x, y, ref_z + attach_depths[1]], orientation=ARM_ORIENTATION, speed=60)
        time.sleep(0.1)

        move_arm(arm="left_arm", position=[x, y, ref_z + 0.005], orientation=ARM_ORIENTATION, speed=250)
        time.sleep(0.1)

    move_arm_js(arm="left_arm", joint_angles=ATTACH_JOINTS, speed=1.5)

    print_log("epipette_attach_test complete")
    return {"success": True}
