import time

from protocol_schema import SkillObject
from utils import PRE_ASPIRATE_JOINTS

from .modules import (
    EPIPETTE_GREY,
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    epipette_aspirate as _epipette_aspirate_helper,
    get_world_state,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
)


def epipette_grey_aspirate(object: SkillObject, anchor: str, volume: float = 5, speed: float = 5):
    """Left arm aspirates from a named anchor on an object using the grey epipette.

    Args:
        object: Object to aspirate from.
        anchor: Anchor name from the object's yaml file (e.g. 'A1', 'H12').
        volume: Volume to aspirate in µL.
        speed: Pipette speed.
    """
    object_id = object.id
    anchor_name = anchor
    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.8)

    anchor = load_object_anchor(object_id, anchor_name)
    orientation = compute_dispense_orientation(0, 0)
    tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(anchor["xyz"], orientation)

    dx, dy = get_world_state(object_id).get("calibration", {}).get(str(anchor_name), [0.0, 0.0])
    print_log(f"calibration: {dx}, {dy}")
    tcp_position[0] += dx
    tcp_position[1] += dy

    print_log(f"epipette_grey_aspirate: object_id={object_id}, anchor={anchor_name}, volume={volume}, speed={speed}")
    print_log(f"TCP: {tcp_position}")

    move_arm(
        arm="left_arm",
        position=[tcp_position[0], tcp_position[1], tcp_position[2] + 0.15],
        orientation=tcp_orientation,
        speed=250,
    )
    time.sleep(0.1)

    move_arm(
        arm="left_arm",
        position=[tcp_position[0], tcp_position[1], tcp_position[2] - 0.01],
        orientation=tcp_orientation,
        speed=100,
    )
    time.sleep(0.1)

    # dip depth varies by vessel geometry: coldblock_large=-0.070, coldblock_small=-0.053, PCR plate=-0.0335
    z_dip = (
        -0.05 if object_id.startswith("coldblock_large") else -0.055 if object_id.startswith("coldblock_small") else -0.0325
    )
    

    time.sleep(0.1)

    move_arm(
        arm="left_arm",
        position=[tcp_position[0], tcp_position[1], tcp_position[2] + z_dip],
        orientation=tcp_orientation,
        speed=5,
    )

    time.sleep(1)

    _epipette_aspirate_helper(name=EPIPETTE_GREY, volume=volume, speed=speed)
    time.sleep(0.5)

    move_arm(
        arm="left_arm",
        position=[tcp_position[0], tcp_position[1], tcp_position[2] + 0.15],
        orientation=tcp_orientation,
        speed=100,
        wait=True,
    )
    time.sleep(0.1)

    print_log("epipette_grey_aspirate complete")
    return {"success": True}
