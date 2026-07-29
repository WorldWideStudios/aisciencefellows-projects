import json

from protocol_schema import SkillObject

from .modules import load_object_anchor, move_arm, print_log, set_gripper


def _parse_anchor_names(anchor_names):
    """Normalize a Skills Editor text value into an ordered anchor-name list."""
    if isinstance(anchor_names, list):
        values = anchor_names
    elif isinstance(anchor_names, str):
        raw_value = anchor_names.strip()
        if not raw_value:
            raise ValueError("anchor_names must not be empty")

        if raw_value.startswith("["):
            try:
                values = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "anchor_names must be a JSON list or comma-separated names"
                ) from exc
            if not isinstance(values, list):
                raise ValueError("anchor_names JSON value must be a list")
        else:
            values = raw_value.split(",")
    else:
        raise ValueError(
            "anchor_names must be a JSON list or comma-separated string"
        )

    if not values:
        raise ValueError("anchor_names must contain at least one anchor")

    normalized_names = []
    for index, anchor_name in enumerate(values):
        if not isinstance(anchor_name, str) or not anchor_name.strip():
            raise ValueError(
                f"anchor_names[{index}] must be a non-empty string"
            )
        normalized_names.append(anchor_name.strip())
    return normalized_names


def move_arm_to_anchor(
    target: SkillObject,
    anchor_names: str,
    arm: str = "right_arm",
    speed: float = 20,
):
    """Move the selected arm directly through an ordered list of anchors.

    Args:
        target: World object that owns the destination anchors.
        anchor_names: Ordered anchor names as a JSON list or comma-separated
            text, for example ["prepose_3", "prepose_2", "prepose_1"].
        arm: Arm to move; must be left_arm or right_arm.
        speed: Relative speed for every Cartesian move in the anchor path.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting move_arm_to_anchor "
        f"(arm={arm}, anchors={anchor_names!r}, speed={speed})"
    )

    if arm not in {"left_arm", "right_arm"}:
        raise ValueError("arm must be 'left_arm' or 'right_arm'")
    if speed <= 0:
        raise ValueError("speed must be positive")

    normalized_names = _parse_anchor_names(anchor_names)

    # Resolve the complete path before commanding any motion. A missing or
    # mistyped anchor therefore fails without moving either arm.
    anchor_path = []
    for anchor_name in normalized_names:
        anchor = load_object_anchor(target.id, anchor_name)
        width_m = anchor.get("width")
        if (
            isinstance(width_m, bool)
            or not isinstance(width_m, (int, float))
            or width_m < 0
        ):
            raise ValueError(
                f"anchor {anchor_name!r} has invalid gripper width {width_m!r}"
            )
        anchor_path.append((anchor_name, anchor, float(width_m)))

    # Intentionally move directly from the current TCP pose to the first anchor,
    # then directly between successive anchors. This skill does not command a
    # joint-space transition pose or move the other arm.
    gripper_widths_m = []
    for index, (anchor_name, anchor, width_m) in enumerate(anchor_path, start=1):
        print_log(
            f"Moving {arm} to anchor {index}/{len(anchor_path)}: "
            f"{anchor_name!r} (gripper_width={width_m}m)"
        )
        move_arm(
            arm=arm,
            position=anchor["xyz"],
            orientation=anchor["rpy"],
            speed=speed,
            wait=True,
        )
        set_gripper(arm=arm, width_m=width_m)
        gripper_widths_m.append(width_m)

    final_anchor = normalized_names[-1]
    final_gripper_width_m = gripper_widths_m[-1]
    print_log(
        f"move_arm_to_anchor completed; {arm} is at {final_anchor!r} "
        f"with gripper width {final_gripper_width_m}m"
    )
    return {
        "success": True,
        "arm": arm,
        "anchor_names": normalized_names,
        "final_anchor": final_anchor,
        "gripper_widths_m": gripper_widths_m,
        "final_gripper_width_m": final_gripper_width_m,
        "target_object_id": target.id,
    }
