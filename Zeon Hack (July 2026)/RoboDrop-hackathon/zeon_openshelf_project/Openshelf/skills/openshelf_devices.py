"""Shared helper for actuating front-panel instruments. Imported by press_button and
actuate_module so the press-and-photograph pattern has exactly one implementation.

Lives at skills/openshelf_devices.py. The skill loader adds skills/ to sys.path, so this
resolves as a top-level module -- the same mechanism the existing skills use for utils.py.
"""

from execution.execution_functions import (
    anchor_preapproach,
    capture_image,
    load_object_anchor,
    move_arm,
    move_relative,
    pause_aware_sleep,
    print_log,
    set_gripper,
)

# A button travels a millimetre or two. Beyond this a "press" is driving into the panel.
MAX_PRESS_DEPTH_M = 0.015
# Above this a contact anchor is really a grasp anchor, and pressing with open fingers can
# catch adjacent controls.
CONTACT_WIDTH_EPS_M = 0.001


def look_and_capture(device_id, view_anchor, arm, name, speed=20.0, settle_s=0.4):
    """Point the wrist camera at a display and take a still. Returns the path, or None.

    capture_image returns a path or None -- it does not raise -- so a None return is the
    signal that there is no evidence, and it must be checked rather than assumed.
    """
    try:
        view = load_object_anchor(device_id, view_anchor)
    except Exception as exc:
        print_log(f"look_and_capture: no view anchor {view_anchor!r} ({exc})")
        return None
    move_arm(arm, view["xyz"], view["rpy"], speed=speed)
    pause_aware_sleep(settle_s)
    path = capture_image(arm, name, save_to_project=True)
    if path is None:
        print_log(f"look_and_capture: capture {name!r} did not succeed")
        return None
    print_log(f"look_and_capture: saved {name!r}")
    return path


def press_and_capture(
    device_id,
    button_anchor,
    view_anchor="view_front",
    arm="right_arm",
    press_depth_m=0.004,
    dwell_s=0.6,
    speed=20.0,
    press_speed=5.0,
    capture_before=True,
):
    """Press a physical button with a closed gripper, photographing the display either side.

    Returns a dict with `success`, `verifiable`, and the capture names. `verifiable` is
    separate from `success` on purpose: the motion can complete with no camera evidence, and
    reporting that as a confirmed press is the failure this whole pattern exists to avoid.
    """
    if arm not in ("left_arm", "right_arm"):
        print_log(f"press_and_capture: refusing invalid arm {arm!r}")
        return {"success": False, "reason": "invalid_arm"}
    if not (0.0 <= press_depth_m <= MAX_PRESS_DEPTH_M):
        print_log(f"press_and_capture: refusing press_depth_m={press_depth_m} "
                  f"(outside 0..{MAX_PRESS_DEPTH_M * 1000:.0f} mm)")
        return {"success": False, "reason": "implausible_press_depth"}

    try:
        btn = load_object_anchor(device_id, button_anchor)
    except Exception as exc:
        print_log(f"press_and_capture: no anchor {button_anchor!r} on {device_id} ({exc})")
        return {"success": False, "reason": "missing_button_anchor"}

    width = btn.get("width")
    if width is not None and width > CONTACT_WIDTH_EPS_M:
        print_log(f"press_and_capture: {button_anchor} declares grasp.width={width}; that is a "
                  f"grasp anchor, not a contact. Refusing to press with open fingers.")
        return {"success": False, "reason": "anchor_is_a_grasp_not_a_contact"}

    set_gripper(arm, 0.0)

    before = None
    if capture_before:
        before = look_and_capture(device_id, view_anchor, arm,
                                  f"{device_id}_{button_anchor}_before", speed=speed)
        if before is None:
            print_log("press_and_capture: no before-frame; the press will be harder to judge")

    rpy = btn["rpy"]
    pre = anchor_preapproach(btn)
    move_arm(arm, pre, rpy, speed=speed)
    move_arm(arm, btn["xyz"], rpy, speed=press_speed)
    # Along the anchor's own +Z, so a side-mounted button is pressed sideways. delta_rpy is
    # omitted, which the runtime documents as holding orientation.
    move_relative(arm, [0.0, 0.0, press_depth_m], speed=press_speed)
    pause_aware_sleep(dwell_s)
    move_arm(arm, pre, rpy, speed=speed)

    after = look_and_capture(device_id, view_anchor, arm,
                            f"{device_id}_{button_anchor}_after", speed=speed)
    if after is None:
        print_log("press_and_capture: NO after-frame -- the press is UNVERIFIED. No "
                  "independent channel confirms the instrument state changed.")

    return {
        "success": True,
        "device": device_id,
        "button": button_anchor,
        "verifiable": after is not None,
        "before_capture": before,
        "after_capture": after,
        "note": "Motion completed. Read the captured frame(s) against the device manual to "
                "confirm the state changed; this helper does not judge that.",
    }
