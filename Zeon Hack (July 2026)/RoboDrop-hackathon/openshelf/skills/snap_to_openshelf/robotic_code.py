from common_models.transform import rpy_to_quat_wxyz

from .modules import (
    get_object_pose,
    load_object_anchor,
    print_log,
    snap_object_anchor_to_world_pose,
)

# The dispensed item is represented by `tipbox_grey`, pre-placed in the world.
OBJECT = "tipbox_grey"
OBJECT_ANCHOR = "Tipbox Openshelf Grasp Anchor"
TARGET_OBJECT = "openshelf"
TARGET_ANCHOR = "Openshelf Plate Anchor"

# Lift the snap slightly in world +Z so the tipbox sits on the shelf instead of
# clipping into it. Tune here.
SNAP_Z_OFFSET = 0.02


def snap_to_openshelf():
    """Reposition the dispensed object onto the OpenShelf plate anchor (upright).

    Mate the tipbox's grasp anchor to the live plate anchor's pose (position +
    orientation), using the anchor rpy as-is so the box sits upright (mirrors
    snap_into_openshelf).
    """
    print_log(runlog=True, runlog_type="step_start")

    target = load_object_anchor(TARGET_OBJECT, TARGET_ANCHOR)
    xyz = [float(v) for v in target["xyz"]]
    xyz[2] += SNAP_Z_OFFSET

    # Use the plate anchor's own rpy (world pitch -90°); it lands the box upright.
    r, p, y = target["rpy"]
    wxyz = [float(v) for v in rpy_to_quat_wxyz([r, p, y])]

    try:
        obj = get_object_pose(OBJECT)
    except ValueError:
        print_log(f"object '{OBJECT}' not in world — nothing to snap")
        return {"success": False, "error": f"object '{OBJECT}' not in world"}

    snap_object_anchor_to_world_pose(obj["object_id"], OBJECT_ANCHOR, xyz, wxyz)
    print_log(f"snapped {OBJECT}/{OBJECT_ANCHOR} -> {TARGET_OBJECT}/{TARGET_ANCHOR}; wxyz={wxyz}")
    return {"success": True, "object": OBJECT, "target_xyz": xyz}
