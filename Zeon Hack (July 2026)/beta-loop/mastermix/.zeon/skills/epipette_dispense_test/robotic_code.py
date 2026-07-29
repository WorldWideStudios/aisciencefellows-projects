import time

from protocol_schema import SkillObject
from utils import PRE_ASPIRATE_JOINTS, object_display_name

from .modules import (
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    get_world_state,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
)


def epipette_dispense_test(
    object: SkillObject,
    pipette: SkillObject,
    use_calibration: bool = True,
):
    """Loop over every well running the epipette_dispense motion, but never descend into the well.

    Same targeting as epipette_dispense (well-top anchor + stored tcp_offset + per-well
    calibration_<pipette_name> XY), doing every move except the slow descent into the
    well — hover, descend to the rim, retract. A calibration sweep to eyeball each well.
    """
    object_id = object.id
    pipette_id = pipette.id
    pipette_name = object_display_name(pipette)

    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.8)

    stored = get_world_state(pipette_id).get("tcp_offset")
    tcp_offset = [float(v) for v in stored] if (stored is not None and len(stored) == 3) else None

    calib_key = f"calibration_{pipette_name}"
    calibration = get_world_state(object_id).get(calib_key, {})
    orientation = compute_dispense_orientation(0, 0)
    wells = list(calibration.keys())
    print_log(f"Starting epipette_dispense_test (object={object_id}, wells={len(wells)})")

    for anchor_name in wells:
        anchor_pose = load_object_anchor(object_id, anchor_name)
        tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(
            anchor_pose["xyz"], orientation, tcp_offset=tcp_offset
        )

        if use_calibration:
            dx, dy = calibration.get(str(anchor_name), [0.0, 0.0])
            tcp_position[0] += dx
            tcp_position[1] += dy

        x, y = tcp_position[0], tcp_position[1]
        well_top_z = tcp_position[2]
        print_log(f"epipette_dispense_test: well {anchor_name} -> TCP z {well_top_z}")

        # 1) Hover above the well top.
        move_arm(arm="left_arm", position=[x, y, well_top_z + 0.01], orientation=tcp_orientation, speed=250)

        # 2) Descend to the rim.
        move_arm(arm="left_arm", position=[x, y, well_top_z - 0.005], orientation=tcp_orientation, speed=50)
        time.sleep(0.1)

        # 3) Retract back to the hover height.
        move_arm(arm="left_arm", position=[x, y, well_top_z + 0.01], orientation=tcp_orientation, speed=250)

    print_log("epipette_dispense_test complete")
    return {"success": True}
