from protocol_schema import SkillObject

from .modules import (
    load_object_anchor,
    print_log,
    snap_object_anchor_to_world_pose,
)


def move_beaker_to_openshelf(
    beaker: SkillObject,
    openshelf: SkillObject,
    shelf_anchor: str,
    beaker_anchor: str = "object",
):
    """Snap a beaker anchor onto a named OpenShelf anchor.

    This V1 skill updates the Zeon world model only. It does not command arm
    motion, close a gripper, or verify that the physical beaker moved.

    Args:
        beaker: Beaker object to move in the world model.
        openshelf: OpenShelf object that provides the target anchor.
        shelf_anchor: Anchor on the OpenShelf object to align the beaker to.
        beaker_anchor: Anchor on the beaker to place at the OpenShelf anchor.
    """
    shelf_anchor = shelf_anchor.strip()
    beaker_anchor = beaker_anchor.strip()
    if not shelf_anchor:
        raise ValueError("shelf_anchor must name an OpenShelf anchor")
    if not beaker_anchor:
        raise ValueError("beaker_anchor must name a beaker anchor")

    print_log(runlog=True, runlog_type="step_start")
    print_log(
        "Starting move_beaker_to_openshelf "
        f"(beaker_anchor={beaker_anchor}, shelf_anchor={shelf_anchor})"
    )

    target = load_object_anchor(openshelf.id, shelf_anchor)
    current = load_object_anchor(beaker.id, beaker_anchor)

    print_log(
        "move_beaker_to_openshelf: "
        f"openshelf {openshelf.id}.{shelf_anchor} "
        f"xyz={target['xyz']} wxyz={target['wxyz']}"
    )
    print_log(
        "move_beaker_to_openshelf: "
        f"beaker {beaker.id}.{beaker_anchor} current "
        f"xyz={current['xyz']} wxyz={current['wxyz']}"
    )

    snap_object_anchor_to_world_pose(
        beaker.id,
        beaker_anchor,
        target["xyz"],
        target["wxyz"],
    )

    print_log("move_beaker_to_openshelf completed")
    return {
        "success": True,
        "beaker_anchor": beaker_anchor,
        "shelf_anchor": shelf_anchor,
        "target_xyz": target["xyz"],
        "target_wxyz": target["wxyz"],
    }
