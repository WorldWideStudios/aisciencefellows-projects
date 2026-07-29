import math
import time

import numpy as np
from common_models.transform import quat_wxyz_to_R, quat_wxyz_to_rpy, rpy_to_quat_wxyz
from common_models.types import JointState, Pose
from protocol_schema import SkillObject

from .modules import (
    detach_object_from_arm,
    get_arm_pose,
    load_object_anchor,
    move_arm,
    print_log,
    set_gripper,
    snap_object_anchor_to_world_pose,
)

# Straight-down place orientation the drop was tuned for, holding the plate at the
# canonical grasp anchor below. Its yaw is carried onto whatever grip is actually
# held (a pure rotation about Z), so an off-frame grasp still places straight down.
PLACE_RPY = [0, 0.0, 0.0]
REFERENCE_GRASP_ANCHOR = "grasp_shortside"


def rotate_joint_6(arm: str, rotation_angle_rad: float = 2 * math.pi, speed: float = 0.5) -> bool:
    """Rotate joint 6 (wrist roll, index 5) by ``rotation_angle_rad``, other joints fixed.

    A full 2*pi turn leaves the TCP orientation unchanged but unwinds the wrist joint,
    giving IK headroom when the commanded seating would otherwise wind joint 6 to its
    limit. With TCP Z straight down, joint-6 rotation is a pure plate yaw about vertical.

    Args:
        arm: "left_arm" or "right_arm".
        rotation_angle_rad: Positive = counterclockwise, negative = clockwise.
        speed: Joint speed.

    Returns:
        True on success. Raises RuntimeError on driver failure.
    """
    from execution.execution_functions import hw

    arm_obj = hw.left_arm if arm == "left_arm" else hw.right_arm

    res = arm_obj.get_joint_state()
    if not res.success:
        raise RuntimeError(f"Failed to get joint state for {arm}")
    positions = np.array(res.data.positions)
    positions[5] += rotation_angle_rad

    target = JointState(names=arm_obj.arm_joint_names, positions=positions)
    res = arm_obj.set_joint_positions(js=target, speed=speed, wait=True)
    if not res.success:
        raise RuntimeError(f"Failed to rotate joint 6 for {arm}: {res.message()}")
    return True


def wellplate_drop(
    object: SkillObject,
    destination: SkillObject,
    destination_anchor: str = "home",
    grasp_anchor: str = "grasp_shortside",
):
    """Drop a held well plate onto a destination anchor with the right arm.

    Moves so the plate's ``bottom_center`` lands on ``destination_anchor``, opens
    the gripper to release, then snaps the plate onto the anchor so sim seats it
    exactly where it was placed.

    Two branches, selected by ``grasp_anchor`` (the anchor the plate was picked at):

    * **Simple (default)** — for a canonical grip (e.g. ``grasp_shortside``), place
      straight down (``PLACE_RPY``) and drop the plate's ``bottom_center`` onto the
      destination anchor (default the holder's ``home``). No grip-relative correction.
    * **Longside (complicated)** — for a ``grasp_longside`` grip (rotated ~90 deg about
      Z and gripping ~38.7 mm off-centre), the straight-down shortside placement is
      carried onto the actual grip via the relative grip rotation, and the descent
      position is recomputed under the commanded orientation so ``bottom_center`` still
      lands on the anchor.

    Args:
        object: The well plate held by the right arm, to drop.
        destination: The object to place onto (must define destination_anchor).
        destination_anchor: Anchor on the destination to align the plate's
            bottom_center to (default the holder's ``home``).
        grasp_anchor: Anchor the plate is held at (as passed to ``wellplate_grab``).
            A ``grasp_longside`` grip takes the grip-aware placement; anything else
            takes the simple straight-down snap.
    """
    print_log(runlog=True, runlog_type="step_start")
    object_id = object.id
    destination_id = destination.id
    print_log(f"Starting wellplate_drop: plate {object_id} -> {destination_anchor} (grasp={grasp_anchor})")

    # Live grip: rigid TCP->bottom_center transform (constant while held).
    tcp = get_arm_pose(arm="right_arm")
    W_tcp = Pose(np.asarray(tcp[:3], dtype=float), rpy_to_quat_wxyz(np.asarray(tcp[3:], dtype=float)))
    bc = load_object_anchor(object_id, "bottom_center")
    W_bc = Pose(np.asarray(bc["xyz"], dtype=float), np.asarray(bc["wxyz"], dtype=float))
    grip = W_tcp.inv() @ W_bc

    place = load_object_anchor(destination_id, destination_anchor)

    if "longside" in grasp_anchor:
        # Complicated grip-aware placement for the off-centre, ~90-deg-rotated longside
        # grip. Canonical reference grip (grasp_shortside) that PLACE_RPY was tuned for,
        # loaded from the same plate so its world pose cancels and this is the pure
        # body-frame TCP->bottom_center transform for the shortside grasp. If the plate
        # has no such anchor, fall back to the actual grip (no relative correction).
        try:
            ref = load_object_anchor(object_id, REFERENCE_GRASP_ANCHOR)
            grip_ref = Pose(np.asarray(ref["xyz"], dtype=float), np.asarray(ref["wxyz"], dtype=float)).inv() @ W_bc
        except Exception:
            print_log(f"wellplate_drop: no {REFERENCE_GRASP_ANCHOR} on plate; using straight-down placement")
            grip_ref = grip

        # Placement orientation: the working straight-down shortside placement, carried
        # onto the actual grip by the relative grip rotation (grip_ref -> grip).
        place_ref = Pose(np.array([0.0, 0.0, 0.0]), rpy_to_quat_wxyz(np.asarray(PLACE_RPY, dtype=float)))
        tcp_target = place_ref @ (grip_ref @ grip.inv())
        place_rpy = quat_wxyz_to_rpy(tcp_target.wxyz).tolist()
        R_place = quat_wxyz_to_R(tcp_target.wxyz)
        unwind_wrist = False  # off-centre grip: a full wrist spin would sweep the plate
    else:
        # Simple snap: seat the plate's bottom_center exactly at the home anchor's own
        # pose. Solve for the gripper orientation that lands bottom_center at the home
        # orientation given the live grip -- NO 180 flip: the anchor already defines the
        # correct seating, so flipping placed the plate 180 deg off (and disagreed with
        # the final snap below, which uses the raw home pose).
        tcp_target = Pose(np.zeros(3), np.asarray(place["wxyz"], dtype=float)) @ grip.inv()
        place_rpy = quat_wxyz_to_rpy(tcp_target.wxyz).tolist()
        R_place = quat_wxyz_to_R(tcp_target.wxyz)
        unwind_wrist = True  # centred grip: safe to unwind the wrist a full turn in place

    # Land bottom_center on the anchor position under the commanded orientation
    # (rotate the grip lever arm by the commanded orientation, not the measured one).
    tcp_xyz = (np.asarray(place["xyz"], dtype=float) - R_place @ np.asarray(grip.xyz, dtype=float)).tolist()
    high = [tcp_xyz[0], tcp_xyz[1], tcp_xyz[2] + 0.05]

    # Seating bottom_center at the correct home orientation can wind joint 6 (wrist roll)
    # to its limit and make the straight-line approach IK-infeasible. A full 2*pi turn of
    # joint 6 keeps the TCP orientation identical (bottom_center still lands on home) but
    # unwinds the wrist so IK has headroom. Shortside only — the grip is centred there, so
    # the plate just spins about its own axis (flip the sign if it winds the wrong way).
    if unwind_wrist:
        rotate_joint_6(arm="right_arm", rotation_angle_rad=-math.pi)

    # Approach from above, descend onto the drop pose, release.
    move_arm(arm="right_arm", position=high, orientation=place_rpy, speed=80)
    move_arm(arm="right_arm", position=tcp_xyz, orientation=place_rpy, speed=20)
    set_gripper(arm="right_arm", width_m=0.10)
    time.sleep(0.5)
    detach_object_from_arm(object_id)

    # Retreat, then snap the plate onto the anchor so sim seats it exactly.
    move_arm(arm="right_arm", position=high, orientation=place_rpy, speed=70)
    snap_object_anchor_to_world_pose(object_id, "bottom_center", place["xyz"], place["wxyz"])

    print_log("wellplate_drop completed")
    return {"success": True}
