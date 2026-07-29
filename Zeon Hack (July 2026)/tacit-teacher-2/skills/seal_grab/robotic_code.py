import time

from protocol_schema import SkillObject
from utils import LEFT_FORWARD_DOWN

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    set_gripper,
)


def seal_grab(
    plate: SkillObject,
    grasp_anchor: str = "seal_approach_1",
    standoff: float | None = None,
):
    """Approach the plate's seal anchor with the left arm and pinch the mat corner.

    Meant to run after the right arm is already holding the plate down (e.g.
    ``wellplate_hold``) — this skill only ever commands the left arm and never
    touches the right arm, so it does not disturb that hold.

    This is deliberately the *approach and pinch* stage only, not a full peel —
    ``seal_advance`` carries the mat along the taught path from here.

    What ``tacit/sessions/peel_seal/`` actually records, as of the Q1-Q6
    interview:

    - The peel runs diagonally, corner to opposite corner, at roughly 45 degrees
      (Q3). The video pass estimated 45-90 and was wrong; the expert corrected
      it and attributed the spread to camera error.
    - Grip the mat *as hard as possible* (Q2): "the mat will not break and
      gripping it strongly gives control to the user." This is bounded below and
      not above — design against a slip, not against crushing the mat. So the
      taught pinch width here should err tight.
    - Speed during the pull is the contamination mechanism (Q4, V5, V6). Nothing
      after the pinch should move faster than the approach did.

    An earlier version of this docstring described a two-stage pull and gripper
    values in raw UFactory device units, citing that session. Both were
    retracted: the answer they came from described a robot the expert has no
    access to, so it was never their technique. See the dated note in
    ``tacit/sessions/peel_seal/10-transcript.md`` at Q2.

    Args:
        plate: The plate object whose seal anchor to approach.
        grasp_anchor: Anchor name on the plate's object model for the seal
            corner (taught with a narrow pinch width for the mat edge).
        standoff: Hover clearance, in metres, for the pre-grip approach pose.
            Pass ``None`` to use the anchor's own taught standoff.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting seal_grab (anchor={grasp_anchor})")

    object_id = plate.id

    grasp = load_object_anchor(object_id, grasp_anchor)
    pick_xyz = grasp["xyz"]
    pick_ori = grasp["rpy"]
    width = grasp.get("width")
    if width is None:
        width = 0.01

    move_arm_js(arm="left_arm", joint_angles=LEFT_FORWARD_DOWN, speed=0.5)

    # Open past the taught pinch width before approaching.
    set_gripper(arm="left_arm", width_m=width + 0.01)
    time.sleep(0.1)

    pre_xyz = anchor_preapproach(grasp, standoff=standoff)
    move_arm(arm="left_arm", position=pre_xyz, orientation=pick_ori, speed=50, wait=True)

    move_arm(arm="left_arm", position=pick_xyz, orientation=pick_ori, speed=20, wait=True)
    time.sleep(0.5)

    set_gripper(arm="left_arm", width_m=width)
    time.sleep(0.2)

    # No attach_object_to_arm: there is no separate seal/mat world object, and
    # the plate itself is already attached to the right arm from the hold step.
    print_log(f"seal_grab completed — left arm pinched at {grasp_anchor}, right arm untouched")
    return {"success": True}
