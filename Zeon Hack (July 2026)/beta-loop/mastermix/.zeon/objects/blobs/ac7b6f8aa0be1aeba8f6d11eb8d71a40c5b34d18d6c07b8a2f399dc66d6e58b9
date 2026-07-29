"""Shared constants and helpers for the pipette_demo skills.

Joint-angle constants (radians, 6-DOF arms) plus small world-lookup helpers
(object_display_name, epipette_device_name, run_label). Imported by individual
skills via ``from utils import <NAME>``. The ``skills/`` directory is added to
``sys.path`` by the skill loader, so this resolves as a top-level module.
"""

from protocol_schema import SkillObject


def object_display_name(obj: SkillObject | str, fallback: str = "") -> str:
    """Return the world-object name (e.g. 'wellplate_pcr_parts_1') for a
    SkillObject or its UID, by looking it up in the live world. Falls back to
    ``fallback`` if the object isn't present."""
    try:
        from execution.execution_functions import hw

        uid = obj.id if isinstance(obj, SkillObject) else str(obj)
        entry = hw.world.objects.get(uid)
        if entry is not None:
            name = entry.metadata.get("name")
            if name:
                return name
    except Exception:
        pass
    return fallback


def epipette_device_name(pipette: SkillObject | str) -> str:
    """Map a pipette *world object* to the *device* name the epipette API wants.

    The plunger calls (``epipette_aspirate`` / ``epipette_dispense`` /
    ``epipette_tip_eject``) address a Bluetooth device by logical name, which is
    a different namespace from the world object — the demo world just happens to
    name its instances after the devices. Resolving it here keeps every skill
    working with either pipette instead of hardcoding one device.

    Instance suffixes are tolerated (``epipette_10ul_2`` -> ``epipette_10ul``).
    """
    from execution.execution_functions import EPIPETTE_10UL, EPIPETTE_120UL

    known = (EPIPETTE_10UL, EPIPETTE_120UL)
    name = object_display_name(pipette)
    for device in known:
        if name == device or name.startswith(f"{device}_"):
            return device
    raise ValueError(
        f"pipette object {name!r} does not map to a known epipette device "
        f"{known}; rename the world instance or extend epipette_device_name()"
    )


def run_label() -> str:
    """Prefix line identifying the current run by its operator-typed name.

    Reads ``name`` from the run's ``metadata.json`` (the value entered in the
    "Name this run" dialog), falling back to the auto-generated ``execution_id``
    when blank and to ``""`` when no execution is bound. Returns a trailing
    newline so it can be prepended directly to a notification message string.
    """
    try:
        import json

        from execution.execution_functions import execution_dir

        d = execution_dir()
        if d is not None:
            meta_path = d / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
                name = (meta.get("name") or "").strip()
                if name:
                    return f"*Run:* {name}\n"
                eid = meta.get("execution_id") or ""
                if eid:
                    return f"*Run:* `{eid}`\n"
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Transition poses — the standard safe waypoints for relocating an arm
# ---------------------------------------------------------------------------
# Use these by default whenever a skill moves an arm between tasks or
# instruments. A ``move_arm_js`` target *is* a joint configuration, so it cannot
# fail IK or flip to an awkward elbow branch the way a long free-space Cartesian
# ``move_arm`` can — and a skill that begins and ends at (or near) one of these
# composes with any other skill without pairwise path planning.
#
# Named on two axes so the names are arm-agnostic:
#   azimuth — FORWARD (over the deck) / OUTER (away from the centerline) /
#             INNER (toward the other arm) / BACK (behind)
#   wrist   — DOWN (gripper at the deck) / FRONT (gripper horizontal, outward)
#
# BACK sits on the seam where joint 1 wraps, so it splits into two branches that
# are the same physical spot one base turn apart — pick the one matching the
# arm's current side so the base never unwinds the long way around.
#
# DUAL-ARM RULE: never command an INNER_* move while the other arm is also
# toward the center. Clear the other arm to an OUTER_*/FORWARD_*/BACK_* pose
# first, as an explicit step.
#
# These are waypoints, never work poses — end a relocation on an anchor-driven
# approach. Re-teach the values here if this bench is calibrated differently;
# skills read them by name, so nothing else has to change.

LEFT_FORWARD_DOWN = [-0.104, -0.681, -0.963, -0.018, 1.626, 1.459]
LEFT_FORWARD_FRONT = [0.085, -0.196, -0.767, -3.020, 0.636, 3.023]
LEFT_OUTER_DOWN = [1.464, -0.695, -0.720, -6.281, 1.416, 4.616]
LEFT_OUTER_FRONT = [1.261, -0.506, -0.448, -4.879, 1.833, 4.080]
LEFT_INNER_DOWN = [-1.331, -0.882, -1.054, 0.002, 1.933, 1.880]
LEFT_INNER_FRONT = [-0.750, -0.317, -0.471, -0.848, 2.141, 2.591]
LEFT_BACK_DOWN_FROM_INNER = [-3.291, -0.576, -1.212, 0.009, 1.784, -0.077]
LEFT_BACK_DOWN_FROM_OUTER = [2.986, -0.577, -0.797, 0.002, 1.374, -0.077]

RIGHT_FORWARD_DOWN = [-0.218, -0.663, -0.989, -0.031, 1.682, 4.491]
RIGHT_FORWARD_FRONT = [0.250, 0.112, -0.858, -1.347, 1.777, 2.382]
RIGHT_OUTER_DOWN = [-1.583, -0.554, -1.089, -0.043, 1.639, 1.595]
RIGHT_OUTER_FRONT = [-0.810, 0.200, -1.095, -1.008, 2.165, 2.442]
RIGHT_INNER_DOWN = [1.675, -0.730, -0.815, 0.043, 1.567, 4.833]
RIGHT_INNER_FRONT = [0.729, -0.236, -0.731, 1.030, 2.242, 3.955]
RIGHT_BACK_DOWN_FROM_INNER = [3.063, -0.335, -1.281, 0.026, 1.584, -0.077]
RIGHT_BACK_DOWN_FROM_OUTER = [-3.095, -0.421, -1.313, 0.008, 1.692, 0.087]

# FORWARD_DOWN doubles as each arm's rest/stow configuration — it is one pose,
# not two, so don't add a separate STOW constant.
LEFT_ARM_STOW_JOINTS = LEFT_FORWARD_DOWN
RIGHT_ARM_STOW_JOINTS = RIGHT_FORWARD_DOWN

# ---- Task poses ------------------------------------------------------------
# NOT transition poses: these sit over specific deck features and are only
# valid for this world. The pipetting skills stage at PRE_ASPIRATE_JOINTS on
# entry and exit so they compose in any order.
PRE_ASPIRATE_JOINTS = [0.375, -0.573, -0.448, -1.423, 1.806, 2.253]
PRE_PICK_JOINTS = [0.527, 0.063, -1.129, -0.000, 1.065, 0.527]
