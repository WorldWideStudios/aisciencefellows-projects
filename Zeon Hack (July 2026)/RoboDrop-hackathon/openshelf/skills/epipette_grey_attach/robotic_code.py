import time

from epipette_grey_eject.robotic_code import epipette_grey_eject
from epipette_tip_check.robotic_code import epipette_tip_check
from utils import run_label

from .modules import (
    ask_user_slack,
    get_object_pose,
    get_world_state,
    move_arm,
    move_arm_js,
    pause_for_user,
    print_log,
    send_slack,
    set_world_state,
)

TIP_HEIGHT = 0.158  # absolute world z of tip tops — calibrated for pipette_demo_world

# Ordered tipbox registry: display name -> world object UUID.
# Tips are consumed from the active rack 1..96; when a rack is exhausted
# (tip 96 used) the next rack in this order becomes active, wrapping back
# to the first after the last. Which rack is active and each rack's tip
# pointer live in live_state.yaml (the `active` flag + `tip_index`).
TIPBOXES = {
    "tipbox_10ul_1": "tipbox_grey_917dd7d2-a4fb-445a-9626-ad70922b2bb3",
    "tipbox_10ul_2": "tipbox_grey_b12a77d3-c9bd-4dd2-aed2-fa667391eb2c",
    "tipbox_10ul_3": "tipbox_grey_6de81d68-0df3-4b1b-a036-2983319d3d09",
}


def _active_tipbox():
    """Return (name, uuid) of the active rack from live state.

    The active rack is the first in TIPBOXES order whose live-state
    `active` flag is True; falls back to the first rack if none is set.
    """
    for name, uuid in TIPBOXES.items():
        if get_world_state(uuid).get("active"):
            return name, uuid
    first = next(iter(TIPBOXES))
    return first, TIPBOXES[first]

ARM_ORIENTATION = [-0.977, -1.555, -2.200]

POST_ATTACH_JOINTS = [0.893, 0.354, -1.207, -0.881, 2.177, 2.538]


def _perform_attach_motion():
    """Run one attach attempt: move to the active tip, latch on, bump tip_index."""
    print_log("Starting epipette_grey_attach")
    move_arm_js(arm="left_arm", joint_angles=POST_ATTACH_JOINTS, speed=0.5)

    tipbox_name, tipbox_id = _active_tipbox()
    state = get_world_state(tipbox_id)
    tip_index = state.get("tip_index", 1)  # 1-based: 1..96

    print_log(f"Active tipbox {tipbox_name} ({tipbox_id}); using tip {tip_index} of 96")

    tipbox_pose = get_object_pose(tipbox_name)
    print_log(tipbox_pose)

    # compute_tip_position_from_index uses 0-based grid math; convert at the boundary
    dx, dy = state.get("calibration", {}).get(str(tip_index), [0.0, 0.0])
    print_log(f"Calibration offset: {dx}, {dy}")
    tip_position = tipbox_pose["xyz"]
    tip_position[0] = tipbox_pose["xyz"][0] + dx
    tip_position[1] = tipbox_pose["xyz"][1] + dy
    tip_position[2] = TIP_HEIGHT

    print_log(f"Moving epipette grey above tip position {tip_index}: {tip_position}")
    move_arm(
        arm="left_arm",
        position=[tip_position[0], tip_position[1], tip_position[2] + 0.07],
        orientation=ARM_ORIENTATION,
        speed=100,
    )
    time.sleep(0.1)

    move_arm(
        arm="left_arm",
        position=[tip_position[0], tip_position[1], tip_position[2] + 0.02],
        orientation=ARM_ORIENTATION,
        speed=60,
    )
    time.sleep(0.1)

    move_arm(
        arm="left_arm",
        position=[tip_position[0], tip_position[1], tip_position[2] + 0.01],
        orientation=ARM_ORIENTATION,
        speed=5,
    )
    time.sleep(0.5)

    move_arm(
        arm="left_arm",
        position=[tip_position[0], tip_position[1], tip_position[2] - 0.0015],
        orientation=ARM_ORIENTATION,
        speed=4,
    )
    time.sleep(0.5)

    move_arm(
        arm="left_arm",
        position=[tip_position[0], tip_position[1], tip_position[2] + 0.2],
        orientation=ARM_ORIENTATION,
        speed=100,
    )
    time.sleep(0.1)

    # Tip consumed. Advance; on rack exhaustion, hand off (or Slack-wait for reload).
    if tip_index < 96:
        set_world_state(tipbox_id, {"tip_index": tip_index + 1})
        print_log(f"Updated {tipbox_name} tip counter to {tip_index + 1}")
    else:
        names = list(TIPBOXES)
        i = names.index(tipbox_name)
        if i + 1 < len(names):
            next_name = names[i + 1]
            send_slack(run_label() + f":large_yellow_square: Tip box `{tipbox_name}` empty — continuing with `{next_name}`.")
            set_world_state(tipbox_id, {"active": False})
            set_world_state(TIPBOXES[next_name], {"active": True, "tip_index": 1})
            print_log(f"Tipbox {tipbox_name} exhausted; switched active rack to {next_name}")
        else:
            send_slack(run_label() + f":small_orange_diamond: Tip box `{tipbox_name}` empty.")
            ask_user_slack(
                run_label() + ":red_circle: All grey tip boxes are empty. Replace them, then click *1* to continue.",
                options={"1": "ready"},
                timeout_s=3600,
                default=None,
            )
            for j, name in enumerate(names):
                set_world_state(TIPBOXES[name], {"active": j == 0, "tip_index": 1})
            print_log("All tipboxes reset by operator; resuming from rack 1 (tip 1)")

    print_log(f"Resolving to post-attach joint config: {POST_ATTACH_JOINTS}")
    move_arm_js(arm="left_arm", joint_angles=POST_ATTACH_JOINTS, speed=1)


def epipette_grey_attach():
    """Attach a tip; verify via laser check; eject and retry once per cycle; pause and loop on repeated failure."""
    while True:
        _perform_attach_motion()
        check = epipette_tip_check()
        if check["tip_present"]:
            return {"success": True}

        print_log(f"Tip check failed (laser value={check.get('value')}); ejecting and retrying on next tip.")
        epipette_grey_eject()
        _perform_attach_motion()
        check = epipette_tip_check()
        if check["tip_present"]:
            return {"success": True}

        print_log(f"Tip check failed after retry (laser value={check.get('value')}); ejecting before operator pause.")
        epipette_grey_eject()
        pause_for_user(
            message=(
                "🟡 *Tip attach failed twice* (laser did not see a tip). "
                "Inspect the epipette and tip rack, then click *Resume* in the UI to retry."
            ),
        )
