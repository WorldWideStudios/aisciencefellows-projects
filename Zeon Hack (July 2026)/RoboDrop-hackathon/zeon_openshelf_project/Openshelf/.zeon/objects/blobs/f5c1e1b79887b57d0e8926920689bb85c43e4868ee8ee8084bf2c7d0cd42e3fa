from execution.execution_functions import *

from openshelf_devices import press_and_capture


def press_button(
    device: SkillObject,
    button_anchor: str,
    view_anchor: str = "view_front",
    arm: str = "right_arm",
    press_depth_m: float = 0.004,
    dwell_s: float = 0.6,
    speed: float = 20.0,
    press_speed: float = 5.0,
    capture_before: bool = True,
):
    """Press a physical button on an instrument, photographing the display as evidence.

    For instruments with no host interface -- a front-panel sealer, an incubator-shaker, a
    centrifuge. The only way to actuate them is a finger, and the only way to know it worked
    is to look at the display afterwards.

    The gripper stays CLOSED. Contact anchors on these models carry grasp.width 0.0 for
    exactly that reason, and this refuses to press through an anchor that declares a real
    width, because that one is a grasp and open fingers can catch adjacent controls.

    Approach and withdrawal run along the anchor's own -Z via anchor_preapproach, so the press
    direction is a property of the object model rather than of this skill.

    Returns `verifiable` separately from `success`. The motion can complete with no camera
    evidence; reporting that as a confirmed press is the failure this pattern exists to avoid.

    Args:
        device: Instrument object carrying the button and view anchors.
        button_anchor: Contact anchor to press.
        view_anchor: Viewpoint anchor for reading the display.
        arm: "left_arm" or "right_arm" -- any other value silently moves the RIGHT arm.
        press_depth_m: How far past the anchor to travel to depress the button.
        dwell_s: Hold at depth before withdrawing.
        speed: Relative speed for the approach.
        press_speed: Relative speed for the press. Keep this low.
        capture_before: Also photograph the display before pressing, for a comparison pair.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"press_button: {device.id}.{button_anchor}")
    return press_and_capture(
        device.id, button_anchor, view_anchor=view_anchor, arm=arm,
        press_depth_m=press_depth_m, dwell_s=dwell_s, speed=speed,
        press_speed=press_speed, capture_before=capture_before,
    )
