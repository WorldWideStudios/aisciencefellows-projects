import time

from protocol_schema import SkillObject
from utils import PRE_ASPIRATE_JOINTS, epipette_device_name

from .modules import (
    epipette_tip_eject,
    move_arm_js,
    print_log,
)

# Cell eject-station joint pose (left arm over the tip-waste chute). Fixed to the
# deck, not the pipette — the same station serves any pipette. A task pose, not a
# transition pose (see utils.py for those).
EJECT_JOINTS = [1.342, 0.430, -1.402, -1.721, 1.374, 2.194]


def epipette_eject(pipette: SkillObject):
    """Eject the tip from an epipette at the cell's eject station.

    Moves the left arm to the fixed eject joint pose and fires the tip-eject for
    the given pipette. Bare bones: no descend/nudges and no verification that
    the tip actually came off.

    Args:
        pipette: The epipette to eject the tip from.
    """
    print_log(runlog=True, runlog_type="step_start")
    device = epipette_device_name(pipette)
    print_log(f"Starting epipette_eject (pipette='{device}')")

    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.5)
    move_arm_js(arm="left_arm", joint_angles=EJECT_JOINTS, speed=0.7)
    epipette_tip_eject(name=device)
    time.sleep(1)

    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.5)

    print_log("epipette_eject completed")
    return {"success": True}
