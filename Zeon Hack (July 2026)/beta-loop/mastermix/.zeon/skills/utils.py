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


def object_world_id(obj: SkillObject | str) -> str:
    """Resolve a world-object id (the UUID key in ``hw.world.objects``) from a
    SkillObject, a raw id, or a world-object *name*.

    A real run hands skills a SkillObject, so ``obj.id`` works. But some paths
    (notably single-skill *simulate*) pass the object param through as its plain
    name string — then ``obj.id`` raises ``'str' object has no attribute 'id'``.
    This accepts all three forms so ``get_world_state``/``set_world_state`` lookups
    never crash on a bare string. Real runs are unaffected (returns ``obj.id``).
    """
    if isinstance(obj, SkillObject):
        return obj.id
    s = str(obj)
    try:
        from execution.execution_functions import hw

        if s in hw.world.objects:
            return s  # already a world id (UUID key)
        for uid, entry in hw.world.objects.items():
            if entry.metadata.get("name") == s:
                return uid
    except Exception:
        pass
    return s  # last resort: hand back the string unchanged (no worse than before)


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


def snap_plate_into_gripper(object_id, arm: str = "right_arm", grasp_anchor: str = "grasp_shortside"):
    """Assert the canonical grip, then attach.

    Snaps the plate so its ``grasp_anchor`` (the point that always sits in the
    gripper) lands exactly at the current TCP, then attaches it to the arm. The
    plate is then held identically on every pick, so downstream placement never has
    to trust the plate's tracked world pose. Call this right after the gripper
    closes on the plate.
    """
    import numpy as np
    from common_models.transform import rpy_to_quat_wxyz
    from execution.execution_functions import (
        attach_object_to_arm,
        get_arm_pose,
        snap_object_anchor_to_world_pose,
    )

    tcp = get_arm_pose(arm=arm)  # [x, y, z, roll, pitch, yaw]
    tcp_xyz = [float(v) for v in tcp[:3]]
    tcp_wxyz = rpy_to_quat_wxyz(np.asarray(tcp[3:], dtype=np.float64)).tolist()
    snap_object_anchor_to_world_pose(object_id, grasp_anchor, tcp_xyz, tcp_wxyz)
    attach_object_to_arm(object_id, arm=arm)


# ---- Pipettes --------------------------------------------------------------
# Two pipettes with non-overlapping ranges. A transfer under 10 uL uses the
# 10 uL pipette, anything else the 120 uL one.
#
# name -> (min_ul, max_ul, tipbox type, BLE serial)
# BLE serial is None when main.py already connects it at boot.
PIPETTES = {
    "epipette_10ul": (0.5, 10.0, "tipbox_10ul", None),
    "epipette_120ul": (10.0, 120.0, "tipbox_120ul", "Picus-46883520"),
}

# main.py's boot init registers every epipette under its world object name
# (epipette_10ul, epipette_120ul), so the plunger device name is just the world
# object name — no aliasing. (Historically the 10 uL was registered as
# "epipette_grey"; that alias is dead now and made every plunger op no-op.)
DEVICE_ALIAS: dict[str, str] = {}

_connected = set()


def pipette_name(pipette) -> str:
    """World object name of a pipette, e.g. 'epipette_120ul'."""
    if isinstance(pipette, str):
        return pipette
    return object_display_name(pipette, fallback="epipette_10ul")


def pipette_limits(pipette) -> tuple:
    """(min_ul, max_ul) this pipette can handle."""
    lo, hi, _, _ = PIPETTES.get(pipette_name(pipette), PIPETTES["epipette_10ul"])
    return lo, hi


def epipette_device(pipette) -> str:
    """Device name to send plunger commands to, connecting it the first time.

    A device that fails to connect is logged and its name returned anyway, so
    the plunger call no-ops exactly as it does today with no pipette attached.
    """
    from execution.execution_functions import print_log

    name = pipette_name(pipette)
    device = DEVICE_ALIAS.get(name, name)
    ble = PIPETTES.get(name, (0, 0, "", None))[3]

    if ble and device not in _connected:
        _connected.add(device)
        try:
            from execution.config import EPIPETTE_ENABLED
            from execution.execution_functions import init_epipette

            if not EPIPETTE_ENABLED:
                print_log(f"epipette_device: EPIPETTE_ENABLED=False, not connecting {device}")
            elif init_epipette(name=device, ble_device_name=ble) is None:
                print_log(f"epipette_device: could not connect {device} ({ble}) — plunger will no-op")
        except Exception as e:
            print_log(f"epipette_device: connecting {device} failed: {e}")
    return device


def find_pipettes() -> dict:
    """{pipette name: (pipette, tipbox)} for every pipette present in the world.

    Picks the tip box whose live state has this pipette's ``attach_depths_*``
    (epipette_attach reads that unguarded), preferring one marked ``active``.
    """
    from execution.execution_functions import get_world_state, hw

    def obj(uid):
        return SkillObject(id=uid, pose=[0.0] * 12)

    found = {}
    for name, (_, _, box_type, _) in PIPETTES.items():
        pipette = next((uid for uid, e in hw.world.objects.items() if e.metadata.get("type") == name), None)
        boxes = [uid for uid, e in hw.world.objects.items() if e.metadata.get("type") == box_type]
        if pipette is None or not boxes:
            continue
        boxes.sort(key=lambda uid: (bool(get_world_state(uid).get(f"attach_depths_{name}")), bool(get_world_state(uid).get("active"))), reverse=True)
        found[name] = (obj(pipette), obj(boxes[0]))
    return found


def pipette_for_volume(volume_ul: float, found: dict):
    """(pipette, tipbox) for one transfer, chosen by its total volume."""
    want = "epipette_10ul" if float(volume_ul) < 10.0 else "epipette_120ul"
    other = "epipette_120ul" if want == "epipette_10ul" else "epipette_10ul"
    return found.get(want) or found.get(other)


def pipette_in_hand(found: dict):
    """The pipette currently held, or None.

    Only checks the real pipettes: epipette_grab's sweep also writes
    ``in_hand: false`` onto epipette_stand_chargeable, whose type also starts
    with "epipette".
    """
    from execution.execution_functions import get_world_state

    for pipette, _ in found.values():
        if get_world_state(pipette.id).get("in_hand"):
            return pipette
    return None


def ensure_pipette(target, found: dict) -> bool:
    """Put ``target`` in the hand. Returns True if it had to swap.

    Always places before grabbing — epipette_place reads waypoints that
    epipette_grab stores in one shared slot, so grabbing first would place the
    old pipette against the new one's home pose.
    """
    from epipette_grab.robotic_code import epipette_grab
    from epipette_place.robotic_code import epipette_place
    from execution.execution_functions import print_log

    held = pipette_in_hand(found)
    if held is not None and held.id == target.id:
        return False

    if held is not None:
        print_log(f"⇄ Swapping {pipette_name(held)} → {pipette_name(target)}", runlog=True, runlog_type="event")
        epipette_place(pipette=held)
    else:
        print_log(f"⇄ Picking up {pipette_name(target)}", runlog=True, runlog_type="event")
    epipette_grab(pipette=target)
    return True


# ---- Tip tracking ----------------------------------------------------------
# A tip box's live ``tip_index`` is its 1-based next tip. Attaching advances it;
# when a box runs out we roll to the next box of the SAME type, and when every
# same-type box is empty we pause for the operator to refill (no pause in sim).


def _tipbox_capacity(box, pip_name) -> int:
    """Number of calibrated tips on ``box`` for this pipette (falls back to 96).

    ``or {}`` guards an empty/``None`` ``calibration_<pipette>`` (a bare
    ``calibration_epipette_120ul:`` in live_state parses to None, not a dict)."""
    from execution.execution_functions import get_world_state

    calib = get_world_state(box.id).get(f"calibration_{pip_name}") or {}
    return len(calib) or 96


def _refill_tipboxes(box_type, boxes):
    """Pause for the operator to refill the empty boxes, then reset their counters.

    No pause in simulation (it would hang a dry run) — just resets and logs.
    """
    from execution.execution_functions import is_sim_mode, pause_for_user, print_log, set_world_state

    if is_sim_mode():
        print_log(f"tips: all {box_type} boxes empty in sim — auto-resetting to tip #1")
    else:
        pause_for_user(f"All {box_type} tip boxes are empty. Refill them, then click Resume.")
    for b in boxes:
        set_world_state(b.id, {"tip_index": 1})


def attach_next_tip(pipette, tipbox) -> int:
    """Attach the next fresh tip and advance the box's counter. Returns the tip index.

    Uses the paired ``tipbox`` while it has tips, otherwise rolls to the next box
    of the same type; if every same-type box is empty it pauses for an operator
    refill (see ``_refill_tipboxes``) and resets. Box-vs-pipette matching is already
    guaranteed by the caller (``pipette_for_volume``), so only same-type boxes are
    ever considered here.
    """
    from execution.execution_functions import get_world_state, hw, print_log, set_world_state

    name = pipette_name(pipette)
    box_type = PIPETTES.get(name, (0.0, 0.0, "", None))[2]
    boxes = [
        SkillObject(id=uid, pose=[0.0] * 12)
        for uid, e in hw.world.objects.items()
        if e.metadata.get("type") == box_type
    ]

    def tips_left(box):
        ti = int(get_world_state(box.id).get("tip_index", 1) or 1)
        return _tipbox_capacity(box, name) - ti + 1

    # The paired box if it still has tips, else the next same-type box that does.
    box = tipbox if tips_left(tipbox) > 0 else next((b for b in boxes if tips_left(b) > 0), None)
    if box is None:
        _refill_tipboxes(box_type, boxes)
        box = tipbox

    ti = int(get_world_state(box.id).get("tip_index", 1) or 1)
    print_log(f"    attaching fresh tip #{ti} from {object_display_name(box, box.id)}")
    from epipette_attach.robotic_code import epipette_attach

    epipette_attach(tipbox=box, pipette=pipette, tip_index=ti)
    set_world_state(box.id, {"tip_index": ti + 1, "active": True})
    return ti


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
