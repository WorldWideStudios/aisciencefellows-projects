"""Shared constants and helpers for the pipette_demo skills.

Joint-angle constants (radians, 6-DOF arms) plus small world-lookup / Slack
helpers (object_display_name, run_label). Imported by individual skills via
``from utils import <NAME>``. The ``skills/`` directory is added to ``sys.path``
by the skill loader, so this resolves as a top-level module.
"""

from protocol_schema import SkillObject


def object_display_name(obj: SkillObject | str, fallback: str = "") -> str:
    """Return the world-object name (e.g. 'wellplate_pcr_4') for a SkillObject
    or its UID, by looking it up in the live world. Falls back to ``fallback``
    if the object isn't present."""
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


def run_label() -> str:
    """Slack prefix line identifying the current run by its operator-typed name.

    Reads ``name`` from the run's ``metadata.json`` (the value entered in the
    "Name this run" dialog), falling back to the auto-generated ``execution_id``
    when blank and to ``""`` when no execution is bound. Returns a trailing
    newline so it can be prepended directly to a Slack message string.
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


# ---- Stow poses (default rest positions) -----------------------------------
LEFT_ARM_STOW_JOINTS = [-0.104, -0.681, -0.963, -0.018, 1.626, 1.459]
RIGHT_ARM_STOW_JOINTS = [-0.218, -0.663, -0.989, -0.031, 1.682, 4.491]

# Alternate stow calibration.
LEFT_ARM_STOW_JOINTS_ALT = [0.107, -0.719, -0.512, -0.023, 1.219, 1.679]
RIGHT_ARM_STOW_JOINTS_ALT = [-0.238, -0.732, -0.482, -0.036, 1.244, 4.484]

# ---- Swing poses -----------------------------------------------------------
LEFT_ARM_OUTER_SWING_JOINTS = [2.077, -0.577, -0.835, 0.002, 1.414, 5.229]
RIGHT_ARM_OUTER_SWING_JOINTS = [-2.145, -0.450, -0.957, -0.036, 1.380, 1.041]
LEFT_ARM_INNER_SWING_JOINTS = [-2.663, -0.416, -1.340, 0.004, 1.750, 0.551]
RIGHT_ARM_INNER_SWING_JOINTS = [1.675, -0.730, -0.815, 0.043, 1.567, 4.833]

# ---- Epipette workflow poses -----------------------------------------------
PRE_ASPIRATE_JOINTS = [0.375, -0.573, -0.448, -1.423, 1.806, 2.253]
PRE_PICK_JOINTS = [0.527, 0.063, -1.129, -0.000, 1.065, 0.527]
