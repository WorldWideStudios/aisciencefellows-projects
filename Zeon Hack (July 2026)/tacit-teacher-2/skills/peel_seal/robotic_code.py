import math
import time

from execution.skill_editing import shared_state
from protocol_schema import SkillObject
from utils import PRE_PICK_JOINTS, RIGHT_FORWARD_DOWN, object_display_name

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    move_relative,
    print_log,
    set_gripper,
    set_skill_variable,
)

# ---------------------------------------------------------------------------
# PROVENANCE
#
# Every parameter below traces to tacit/sessions/peel_seal/20-extracted.yaml,
# and through it to either a transcript question or a video timestamp:
#
#   peel_angle_deg = 45      Q3 — corrects the video estimate, which read 45-90
#   grip as hard as possible Q2 — the mat does not break; grip strength is what
#                            gives control. Bounded below, not above.
#   slow, non-accelerating   Q4 + V4@00:22 — speed is the contamination mechanism
#   retry once on a sealed mat  Q5 — and only if nothing spilled and the plate
#                               has not moved
#
# The optional re-grip below has NO expert source. An earlier answer claiming
# the arm needs two pulls was retracted — it described a robot the expert has no
# access to. It is off by default and stays a bench question until someone tests
# whether one continuous pull works.
#
# Geometry is NOT in this file. The peel direction is the vector between two
# taught anchors, and the lift axis is the start anchor's own approach axis.
# Re-teach the anchors and the motion follows with no code change.
# ---------------------------------------------------------------------------


def peel_seal(
    plate: SkillObject,
    peel_start_anchor: str = "peel_corner",
    peel_end_anchor: str = "peel_end",
    peel_angle_deg: float = 45.0,
    steps: int = 8,
    regrasp_after_step: int = 0,
    regrasp_descend_m: float = 0.004,
    grip_open_extra_m: float = 0.02,
    standoff: float = 0.06,
    settle_s: float = 0.5,
    approach_speed: int = 50,
    peel_speed: int = 30,
):
    """Peel a rubber sealing mat off a deep-well plate with the left arm.

    The plate must be held flat. On the bench a human does this with their other
    hand — "two forces, one from the side, one against the table" — so here the
    plate must be seated in a fixture before this skill runs. Without it the
    plate lifts with the mat (failure mode ``plate_lifted``).

    Motion is derived from two taught anchors rather than from numbers here:
    ``peel_start_anchor`` is the gripped corner, ``peel_end_anchor`` is the
    opposite corner, and the peel advances along the vector between them while
    rising along the start anchor's approach axis. At the taught 45 degrees the
    rise per step equals the advance per step.

    The peel is broken into ``steps`` increments rather than one continuous
    slide, because the technique releases only a few wells at a time.

    Grip the mat hard. Q2: "as hard as humanly possible, because the mat will
    not break and gripping it strongly gives control." This parameter is bounded
    below and not above — a slip is the failure to design against, and crushing
    the mat is not a risk. Optional mid-peel re-gripping exists
    (``regrasp_after_step``) but is OFF by default and has no expert source: the
    answer that once justified it described a robot the expert cannot use, and
    was retracted. Try one continuous pull first.

    VERIFICATION IS NOT IMPLEMENTED HERE, but it is now possible. Q4 defines
    success as three conditions — mat detached, nothing transferred between
    wells, plate undisturbed. When this was written no camera function was in
    use anywhere in the project; ``capture_image(arm, capture_name,
    save_to_project)`` has since turned up, driven off the right arm's wrist
    camera (see ``left_arm_pose_sequence_1``). A still after the peel would give
    a human all three checks at once.

    Until that is wired in, this skill performs the motion and cannot confirm
    the outcome. It logs ``verified: False``. Do not read a completed run as a
    successful peel.

    Args:
        plate: The plate carrying the sealing mat.
        peel_start_anchor: Anchor at the mat corner where the peel begins.
        peel_end_anchor: Anchor at the opposite corner; sets the peel direction.
        peel_angle_deg: Angle of the peel above the plate surface. 45 is the
            taught value (Q3); the video estimate of 45-90 was camera error.
        steps: Number of increments the peel is divided into.
        regrasp_after_step: Step index after which the gripper releases and
            re-grips further along the mat. ``0`` disables it, which is the
            default — no expert source supports a two-stage pull. Set it only
            after establishing on the bench that one pull does not work.
        regrasp_descend_m: How far to descend onto the lifted mat before closing
            on the re-grip. Needs tuning on the bench.
        grip_open_extra_m: Clearance added to the anchor's taught width when
            opening.
        standoff: Hover clearance above the start anchor, in metres.
        settle_s: Dwell after descending, before closing the gripper.
        approach_speed: Speed for free-space approach moves.
        peel_speed: Speed for every move that has the mat in the gripper. Must
            not exceed approach_speed — Q4 names acceleration during the peel as
            the mechanism that contaminates the wells.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        f"Starting peel_seal (start={peel_start_anchor}, end={peel_end_anchor}, "
        f"angle={peel_angle_deg}, steps={steps})"
    )

    if peel_speed > approach_speed:
        raise ValueError(
            f"peel_speed ({peel_speed}) exceeds approach_speed ({approach_speed}). "
            "The peel must never be the fast part of this skill — speed during "
            "the pull is what moves liquid between wells (Q4, V5, V6)."
        )
    if steps < 1:
        raise ValueError(f"steps must be >= 1, got {steps}")

    object_id = plate.id

    start = load_object_anchor(object_id, peel_start_anchor)
    end = load_object_anchor(object_id, peel_end_anchor)

    start_xyz = start["xyz"]
    start_rpy = start["rpy"]
    width = start.get("width") or 0.01

    # Peel direction: the taught diagonal, start corner to opposite corner.
    diag = [end["xyz"][i] - start_xyz[i] for i in range(3)]
    span = math.sqrt(sum(c * c for c in diag))
    if span < 1e-6:
        raise ValueError(
            f"anchors {peel_start_anchor!r} and {peel_end_anchor!r} resolve to "
            f"the same point ({span:.6f} m apart) — the peel direction is "
            f"undefined. Re-teach them at opposite corners of the mat."
        )
    u_diag = [c / span for c in diag]

    # Lift axis: back off along the start anchor's own approach axis (local -Z),
    # exactly as a pre-approach point is derived. This is "up" relative to the
    # plate, not to the world, so a tilted plate still peels correctly.
    pre_xyz = anchor_preapproach(start, standoff=standoff)
    up = [pre_xyz[i] - start_xyz[i] for i in range(3)]
    up_norm = math.sqrt(sum(c * c for c in up))
    if up_norm < 1e-9:
        raise ValueError(
            f"anchor {peel_start_anchor!r} has no usable approach axis — "
            f"anchor_preapproach returned the anchor point itself."
        )
    u_up = [c / up_norm for c in up]

    advance = span / steps
    rise = advance * math.tan(math.radians(peel_angle_deg))
    delta = [advance * u_diag[i] + rise * u_up[i] for i in range(3)]

    print_log(
        f"peel span {span:.4f} m over {steps} steps: {advance * 1000:.1f} mm "
        f"advance and {rise * 1000:.1f} mm rise per step"
    )

    set_skill_variable(
        "peel_seal_plan",
        {"span_m": span, "steps": steps, "advance_m": advance, "rise_m": rise},
    )

    # Clear the other arm before working toward the centre of the deck.
    move_arm_js(arm="right_arm", joint_angles=RIGHT_FORWARD_DOWN, speed=0.5)
    move_arm_js(arm="left_arm", joint_angles=PRE_PICK_JOINTS, speed=0.5)

    # --- stage 1: take the corner ---------------------------------------- #
    set_gripper(arm="left_arm", width_m=width + grip_open_extra_m)
    time.sleep(0.1)

    move_arm(arm="left_arm", position=pre_xyz, orientation=start_rpy,
             speed=approach_speed, wait=True)
    move_arm(arm="left_arm", position=start_xyz, orientation=start_rpy,
             speed=peel_speed, wait=True)
    time.sleep(settle_s)

    set_gripper(arm="left_arm", width_m=width)
    time.sleep(0.2)

    # --- the peel ---------------------------------------------------------- #
    for step in range(1, steps + 1):
        move_relative(arm="left_arm", delta_xyz=delta, speed=peel_speed)

        # Optional, off by default, and NOT expert knowledge — see the header.
        # Release, settle onto the mat already lifted, take a fresh grip.
        if regrasp_after_step and step == regrasp_after_step and step < steps:
            print_log(f"regrasp after step {step} (no expert source; opt-in)")
            set_gripper(arm="left_arm", width_m=width + grip_open_extra_m)
            time.sleep(0.2)
            move_relative(
                arm="left_arm",
                delta_xyz=[-regrasp_descend_m * c for c in u_up],
                speed=peel_speed,
            )
            time.sleep(settle_s)
            set_gripper(arm="left_arm", width_m=width)
            time.sleep(0.2)

    # --- clear, still holding the mat -------------------------------------- #
    # The mat stays in the gripper. Setting it down plug-side up is a separate
    # concern: laying it plug-side down contaminates the bench (failure mode
    # mat_face_down, V9@00:26), and that belongs in its own skill rather than
    # tacked onto the end of this one.
    move_relative(arm="left_arm", delta_xyz=[standoff * c for c in u_up],
                  speed=peel_speed)

    # End where we started, so this composes with whatever runs next. Still
    # holding the mat — a separate skill sets it down plug-side up.
    move_arm_js(arm="left_arm", joint_angles=PRE_PICK_JOINTS, speed=0.5)

    shared_state.peel_seal_last = {
        "object": object_display_name(plate),
        "span_m": span,
        "steps": steps,
        "angle_deg": peel_angle_deg,
        "verified": False,   # nothing here can confirm the mat actually came off
    }

    print_log(
        "peel_seal motion complete — NOT verified. Check the plate: mat "
        "detached, no liquid between wells, plate undisturbed (Q4)."
    )
    return {"success": True}
