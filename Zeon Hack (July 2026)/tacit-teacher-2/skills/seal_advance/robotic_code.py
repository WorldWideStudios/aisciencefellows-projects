from protocol_schema import SkillObject

from .modules import load_object_anchor, move_arm, print_log


def seal_advance(
    plate: SkillObject,
    grasp_anchor: str = "seal_approach_2",
):
    """Move the left arm to the next seal-peel anchor, keeping its current pinch.

    Companion to ``seal_grab``: run this after ``seal_grab`` has already closed
    the gripper on the mat corner. It never touches the gripper and never
    calls attach — it only moves the arm to the next point along the diagonal
    peel path (``seal_approach_1`` -> ``seal_approach_2`` -> ``seal_approach_3``
    -> ``seal_approach_4`` -> ``seal_approach_5``), continuing the pinch
    already established.

    Args:
        plate: The plate object whose seal anchor to move to.
        grasp_anchor: Anchor name on the plate's object model for the next
            point along the peel path.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting seal_advance (anchor={grasp_anchor})")

    object_id = plate.id
    anchor = load_object_anchor(object_id, grasp_anchor)

    move_arm(arm="left_arm", position=anchor["xyz"], orientation=anchor["rpy"], speed=15, wait=True)

    print_log(f"seal_advance completed — left arm at {grasp_anchor}")
    return {"success": True}
