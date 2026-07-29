from common_models.transform import rpy_to_quat_wxyz

from .modules import (
    get_object_pose,
    load_object_anchor,
    print_log,
    snap_object_anchor_to_world_pose,
)

# Load-direction mirror of snap_to_openshelf: after the store API confirms, place the
# tipbox at the OpenShelf's own object anchor so it visually "goes into" the cabinet.
OBJECT = "tipbox_grey"
OBJECT_ANCHOR = "object"          # the tipbox's placement frame
TARGET_OBJECT = "openshelf"
TARGET_ANCHOR = "object"          # the OpenShelf's object anchor

SNAP_Z_OFFSET = 0.0               # tune in sim


def snap_into_openshelf():
    """Snap the loaded tipbox onto the OpenShelf's object anchor (its stored pose).

    Mate the tipbox's placement frame to the OpenShelf's live object anchor, mirroring
    snap_to_openshelf but for the load direction.
    """
    print_log(runlog=True, runlog_type="step_start")

    target = load_object_anchor(TARGET_OBJECT, TARGET_ANCHOR)
    xyz = [float(v) for v in target["xyz"]]
    xyz[2] += SNAP_Z_OFFSET

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
