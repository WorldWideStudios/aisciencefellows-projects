import time

from epipette_tip_check.robotic_code import epipette_tip_check
from utils import LEFT_ARM_STOW_JOINTS  # noqa: F401  (referenced in commented motion below)

from .modules import (
    EPIPETTE_GREY,
    epipette_tip_eject,
    get_arm_pose,
    move_arm,
    move_arm_js,
    pause_for_user,
    print_log,
)

EJECT_JOINTS = [1.342, 0.430, -1.402, -1.721, 1.374, 2.194]


def _perform_eject_motion():
    """Run one eject attempt: move to eject pose, descend, fire tip eject, ascend back up."""
    print_log("Moving epipette grey to eject joint pose")
    # move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_STOW_JOINTS)
    move_arm_js(arm="left_arm", joint_angles=EJECT_JOINTS, speed=0.7)
    time.sleep(0.1)

    pose = get_arm_pose(arm="left_arm")
    pos = pose[:3]
    orientation = pose[3:]
    print_log(f"Eject pose: {pos}, orientation: {orientation}")

    print_log("Descending 10cm for eject")
    move_arm(
        arm="left_arm",
        position=[pos[0], pos[1] + 0.03, pos[2] - 0.1],
        orientation=orientation,
        speed=250,
    )
    time.sleep(0.1)

    print_log("About to call epipette_tip_eject()")
    time.sleep(0.1)
    epipette_tip_eject(name=EPIPETTE_GREY)
    print_log("Tip eject operation completed!")
    time.sleep(0.1)

    print_log("Ascending back up 10cm")
    move_arm(
        arm="left_arm",
        position=[pos[0], pos[1], pos[2]],
        orientation=orientation,
        speed=250,
    )
    time.sleep(0.1)


def epipette_grey_eject():
    """Eject the tip; verify via laser check; retry the eject motion once on failure; pause for operator if still stuck."""
    _perform_eject_motion()
    check = epipette_tip_check()
    if not check["tip_present"]:
        return {"success": True}

    print_log(f"Post-eject tip check still sees a tip (laser value={check.get('value')}); retrying eject motion.")
    _perform_eject_motion()
    check = epipette_tip_check()
    if not check["tip_present"]:
        return {"success": True}

    print_log(f"Tip still present after retry (laser value={check.get('value')}); pausing for operator.")
    pause_for_user(
        message=(
            "🟡 *Tip eject failed twice* (laser still sees a tip on the epipette). "
            "Manually remove the tip, then click *Resume* in the UI to continue."
        ),
    )
    return {"success": True}
