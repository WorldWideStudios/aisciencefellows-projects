from protocol_schema import SkillObject
from utils import epipette_device, object_display_name

import time
from .modules import (
    EPIPETTE_10UL,
    epipette_tip_eject,
    move_arm_js,
    print_log,
)

# Cell eject-station joint pose (left arm over the tip-waste chute). Fixed to the
# deck, not the pipette — the same station serves any pipette.
EJECT_JOINTS = [1.342, 0.430, -1.402, -1.721, 1.374, 2.194]
PRE_ASPIRATE_JOINTS = [0.375, -0.573, -0.448, -1.423, 1.806, 2.253]

def epipette_eject(pipette: SkillObject):
    """Eject the tip from an epipette at the cell's eject station.

    Moves the left arm to the fixed eject joint pose and fires the tip-eject for the
    given pipette. Bare bones: no descend/nudges and no verification.

    Args:
        pipette: The epipette to eject the tip from.
    """
    print_log(runlog=True, runlog_type="step_start")
    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.5)
    name = object_display_name(pipette, fallback=EPIPETTE_10UL)
    print_log(f"Starting epipette_eject (pipette='{name}')")

    move_arm_js(arm="left_arm", joint_angles=EJECT_JOINTS, speed=0.7)
    epipette_tip_eject(name=epipette_device(pipette))
    time.sleep(1)

    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.5)

    print_log("epipette_eject completed")
    return {"success": True}
