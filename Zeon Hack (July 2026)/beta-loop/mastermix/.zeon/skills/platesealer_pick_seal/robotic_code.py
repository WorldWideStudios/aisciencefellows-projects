from protocol_schema import SkillObject
from utils import LEFT_ARM_INNER_SWING_JOINTS

from .modules import (
    anchor_preapproach,
    load_object_anchor,
    move_arm,
    move_arm_js,
    move_relative,
    print_log,
    set_gripper,
)

# Skill-local left-arm clearance poses on the way in and out of the seal stack.
# Calibrated for this cell; kept verbatim from the original routine, not derived
# from any object model.
INTERMEDIARY_JOINT_ANGLES_IN = [-1.432, -0.158, -0.531, -1.472, 1.660, 4.038]
INTERMEDIARY_JOINT_ANGLES_OUT = [-1.432, -0.159, -0.530, -1.472, 1.660, 4.038]


def platesealer_pick_seal(
    seal_holder_stacked: SkillObject,
    seal_index: int = 1,
    grasp_anchor_prefix: str = "slot",
    approach_anchor: str = "grasp_approach",
    lift_m: float = 0.01,
    start_open_m: float = 0.03,
    approach_speed: float = 50,
    pick_speed: float = 30,
    peel_speed: float = 60,
):
    """Pick a plate seal off a stacked seal holder with the left arm.

    Anchor-driven: the per-seal grasp pose is the
    ``<grasp_anchor_prefix>_<seal_index>`` anchor on the holder's object model, and
    the gripper widths and standoffs come from each anchor's grasp block
    (``load_object_anchor`` returns ``width`` and ``standoff``). Nothing about the
    grasp geometry is baked into this file — add a ``grasp_pose_<n>`` anchor for a
    new stack position and it works with no code change.

    Flow: swing in with the gripper pre-opened to ``start_open_m`` and held there
    through the approach, move through a fixed intermediary clearance pose to the
    approach standoff, down to the grasp standoff, onto the grasp pose, close to the
    grasp anchor's width, then peel the seal free (slide out, lift clear, slide fully
    out) and retreat back through the intermediary pose.

    Args:
        seal_holder_stacked: The stacked seal holder to pick from.
        seal_index: Which seal in the stack — selects the
            ``<grasp_anchor_prefix>_<seal_index>`` anchor (e.g. 1 -> grasp_pose_1).
        grasp_anchor_prefix: Anchor-name prefix for the per-seal grasp pose.
        approach_anchor: Shared approach anchor used to line up before the grasp.
        default_standoff: Fallback standoff (m) when an anchor defines none of its
            own (the grasp anchor's own standoff is preferred when present).
        lift_m: Lift (m) along world +Z to clear the seal above the stack.
        start_open_m: Gripper width the fingers hold from the start through the
            approach, until they close on the seal at the grasp pose.
        approach_speed: Speed for the approach / retreat Cartesian moves.
        pick_speed: Speed for the final descent onto the grasp pose.
        peel_speed: Speed for the peel-off relative moves.
    """
    print_log(runlog=True, runlog_type="step_start")
    print_log(f"Starting platesealer_pick_seal (seal_index={seal_index})")

    holder_id = seal_holder_stacked.id

    # Resolve the grasp pose and the approach from the object model. Widths and
    # standoffs ride along on each anchor's grasp block, so the motion adapts to
    # whatever the anchors declare.
    seal_pick = load_object_anchor(holder_id, f"{grasp_anchor_prefix}_{seal_index}")
    approach_pose = load_object_anchor(holder_id, approach_anchor)

    pick_xyz = seal_pick["xyz"]
    pick_rpy = seal_pick["rpy"]
    grip_width = seal_pick["width"]

    approach = anchor_preapproach(approach_pose, standoff=0.05)
    grasp_preapproach = anchor_preapproach(seal_pick, standoff=0.05)

    print_log(
        f"[platesealer_pick_seal] start_open={start_open_m} grip_width={grip_width} "
        f"grasp_standoff={seal_pick['standoff']}"
    )

    # Swing in with the gripper pre-opened to start_open_m.
    move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_INNER_SWING_JOINTS)
    set_gripper(arm="left_arm", width_m=start_open_m)

    # Through the intermediary clearance pose to the approach standoff, then down
    # onto the grasp pose.
    move_arm_js(arm="left_arm", joint_angles=INTERMEDIARY_JOINT_ANGLES_IN)
    move_arm(arm="left_arm", position=approach, orientation=pick_rpy, speed=approach_speed)
    move_arm(arm="left_arm", position=grasp_preapproach, orientation=pick_rpy, speed=approach_speed)
    move_arm(arm="left_arm", position=pick_xyz, orientation=pick_rpy, speed=pick_speed)


    # Close on the seal, then peel it off the stack: slide out along the approach
    # axis, lift clear (world +Z), slide fully out along the same axis.
    set_gripper(arm="left_arm", width_m=grip_width)
    move_relative(arm="left_arm", delta_xyz=[0, 0, lift_m], speed=peel_speed)
    move_arm(arm="left_arm", position=grasp_preapproach, orientation=pick_rpy, speed=approach_speed)


    # Retreat back through the approach standoff and out via the intermediary pose.
    move_arm(arm="left_arm", position=approach, orientation=pick_rpy, speed=approach_speed)
    move_arm_js(arm="left_arm", joint_angles=INTERMEDIARY_JOINT_ANGLES_OUT)
    move_arm_js(arm="left_arm", joint_angles=LEFT_ARM_INNER_SWING_JOINTS)

    print_log("platesealer_pick_seal completed")
    return {"success": True}
