from execution.execution_functions import *


def localize_cold(
    target: SkillObject,
    view_a: str = "view_a",
    view_b: str = "view_b",
    arm: str = "left_arm",
    tag_edge_m: float = 0.020,
    min_detections: int = 6,
    pos_sigma_gate_mm: float = 15.0,
    cold_start: bool = True,
):
    """Find an object's true world pose from its AprilTags, allowing a large correction.

    Use this when the stored pose is badly wrong -- a first placement, or an object that
    has moved a long way. It differs from a routine relocalization in three ways, all of
    which matter:

      * use_prior is False, so the solve is not anchored on a stored pose that is wrong.
      * max_move_mm is left unset, because that guard rejects large corrections and a
        large correction is the entire point here.
      * min_detections is raised well above the default of 2, which costs nothing on an
        object carrying many tags and rules out a single-tag fluke.

    localize_object_tags visits the viewpoint anchors, so THIS COMMANDS ARM MOTION. It also
    fails soft -- it never raises, it returns a dict with success False and a reason.

    tag_edge_m must match the physical printed tags. A wrong value mis-scales the recovered
    pose, and nothing downstream looks wrong until a grasp misses.

    Args:
        target: The object to relocalize.
        view_a: First viewpoint anchor name on the object.
        view_b: Second viewpoint anchor name on the object.
        arm: Which wrist camera to use.
        tag_edge_m: Printed AprilTag edge length in metres.
        min_detections: Minimum tag observations required to accept the solve.
        pos_sigma_gate_mm: Reject if solved position 1-sigma exceeds this.
        cold_start: True ignores the stored pose. Set False for a routine touch-up.
    """
    print_log(runlog=True, runlog_type="step_start")

    if arm not in ("left_arm", "right_arm"):
        print_log(f"localize_cold: refusing invalid arm {arm!r}")
        return {"success": False, "reason": "invalid_arm"}

    print_log(
        f"localize_cold: {target.id} via [{view_a}, {view_b}] on {arm}, "
        f"tag_edge={tag_edge_m * 1000:.0f} mm, use_prior={not cold_start}"
    )

    loc = localize_object_tags(
        target.id,
        viewpoints=[view_a, view_b],
        arm=arm,
        tag_edge_m=tag_edge_m,
        use_prior=not cold_start,
        min_detections=min_detections,
        pos_sigma_gate_mm=pos_sigma_gate_mm,
        # max_move_mm deliberately omitted -- see the docstring.
    )

    if not loc.get("success"):
        reason = loc.get("reason", "unknown")
        gate = loc.get("gate")
        print_log(f"localize_cold: FAILED reason={reason}" + (f" gate={gate}" if gate else ""))
        # A rejected solve leaves the world pose untouched, so the caller can retry with
        # different viewpoints rather than having to undo anything.
        return {"success": False, "reason": reason, "gate": gate}

    res = loc.get("result") or {}
    moved = loc.get("moved_mm")
    print_log(
        f"localize_cold: accepted. moved {moved} mm, "
        f"{res.get('n_detections')} detections over {res.get('n_tags')} tags, "
        f"pos_sigma {res.get('pos_sigma_mm')} mm, rot_sigma {res.get('rot_sigma_deg')} deg"
    )
    print_log(f"localize_cold: before {loc.get('before')}")
    print_log(f"localize_cold: after  {loc.get('after')}")

    # Report, do not assert. Tag relocalization is flagged experimental, so the numbers go
    # in the run log where a human can see whether the correction was plausible.
    return {
        "success": True,
        "moved_mm": moved,
        "n_detections": res.get("n_detections"),
        "n_tags": res.get("n_tags"),
        "pos_sigma_mm": res.get("pos_sigma_mm"),
        "rot_sigma_deg": res.get("rot_sigma_deg"),
        "after": loc.get("after"),
    }
