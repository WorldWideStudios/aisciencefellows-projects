from common_models.transform import (
    quat_multiply_wxyz,
    quat_wxyz_to_rpy,
    rpy_to_quat_wxyz,
)
from common_models.types import Pose
from execution.execution_functions import *
import numpy as np

TIP_LENGTH = 0.028  # m, physical disposable tip attached to epipette nozzle
TCP_P_PIPETTE_TIP = Pose(xyz=np.array([-0.1139 - TIP_LENGTH, -0.0006, -0.0128]), wxyz=np.array([1.0, 0.0, 0.0, 0.0]))


def compute_tcp_pose_from_tip_position(position, orientation, tcp_offset=None):
    target_tip_position = np.array([position[0], position[1], position[2]])
    world_P_pipette_tip = Pose.from_xyz_rpy(xyz=target_tip_position, rpy=np.array(orientation))
    if tcp_offset is None:
        pipette_tip_P_tcp = TCP_P_PIPETTE_TIP.inv()
    else:
        pipette_tip_P_tcp = Pose(
            xyz=np.array([tcp_offset[0], tcp_offset[1], tcp_offset[2]]),
            wxyz=np.array([1.0, 0.0, 0.0, 0.0]),
        ).inv()
    world_P_tcp = world_P_pipette_tip @ pipette_tip_P_tcp
    return world_P_tcp.xyz.tolist(), world_P_tcp.to_rpy().tolist()


def tcp_tip_offset_from_anchors(grab, tip, tip_extension_m=0.02):
    """TCP->tip translation for a pipette held at its ``grab`` anchor.

    epipette_grab moves the TCP onto the ``grab`` anchor and then attaches, so while
    the pipette is held the TCP frame coincides with the grab-anchor frame. The
    pipette-end ``tip`` anchor expressed in that frame (grab^-1 @ tip) is therefore
    the tip position relative to the hand; the physical disposable tip then extends
    ``tip_extension_m`` further along the pipette axis (the grab->tip direction).

    ``grab`` and ``tip`` are ``load_object_anchor`` dicts (xyz + wxyz). The pipette's
    world placement cancels in grab^-1 @ tip, so this is a fixed hand->tip geometry,
    valid whether the pipette is at its home pose or attached to the arm.

    Returns ``[x, y, z]`` in the TCP frame, for use as the ``tcp_offset`` of
    ``compute_tcp_pose_from_tip_position`` (replaces the hardcoded TCP_P_PIPETTE_TIP).
    """
    world_P_grab = Pose(xyz=np.array(grab["xyz"], dtype=float), wxyz=np.array(grab["wxyz"], dtype=float))
    world_P_tip = Pose(xyz=np.array(tip["xyz"], dtype=float), wxyz=np.array(tip["wxyz"], dtype=float))
    grab_P_tip = world_P_grab.inv() @ world_P_tip
    tip_in_tcp = np.array(grab_P_tip.xyz, dtype=float)
    norm = float(np.linalg.norm(tip_in_tcp))
    axis = tip_in_tcp / norm if norm > 1e-9 else np.array([0.0, 0.0, 1.0])
    return (tip_in_tcp + tip_extension_m * axis).tolist()


def _quat_slerp(q1, q2, t):
    q1 = q1 / np.linalg.norm(q1)
    q2 = q2 / np.linalg.norm(q2)
    dot = np.dot(q1, q2)
    if dot < 0.0:
        q2 = -q2
        dot = -dot
    if dot > 0.9995:
        result = q1 + t * (q2 - q1)
        return result / np.linalg.norm(result)
    theta = np.arccos(np.clip(dot, -1.0, 1.0))
    sin_theta = np.sin(theta)
    return (np.sin((1.0 - t) * theta) / sin_theta) * q1 + (np.sin(t * theta) / sin_theta) * q2


def compute_dispense_orientation(dispense_x, dispense_y):
    default_rpy = np.array([0.78, -1.57, 0.78])
    x_90_rpy = np.array([3.14, 0.0, -1.57])
    y_90_rpy = np.array([-1.57, 0.0, -3.14])
    dispense_x = max(0.0, min(90.0, float(dispense_x)))
    dispense_y = max(0.0, min(90.0, float(dispense_y)))
    x_ratio = dispense_x / 90.0
    y_ratio = dispense_y / 90.0
    default_quat = rpy_to_quat_wxyz(default_rpy)
    x_90_quat = rpy_to_quat_wxyz(x_90_rpy)
    y_90_quat = rpy_to_quat_wxyz(y_90_rpy)
    if dispense_x > 0.0 and dispense_y > 0.0:
        x_intermediate_quat = _quat_slerp(default_quat, x_90_quat, x_ratio)
        default_quat_inv = np.array([default_quat[0], -default_quat[1], -default_quat[2], -default_quat[3]])
        y_relative_quat = quat_multiply_wxyz(default_quat_inv, y_90_quat)
        y_relative_interp_quat = _quat_slerp(np.array([1.0, 0.0, 0.0, 0.0]), y_relative_quat, y_ratio)
        return quat_wxyz_to_rpy(quat_multiply_wxyz(x_intermediate_quat, y_relative_interp_quat)).tolist()
    if dispense_x > 0.0:
        return quat_wxyz_to_rpy(_quat_slerp(default_quat, x_90_quat, x_ratio)).tolist()
    if dispense_y > 0.0:
        return quat_wxyz_to_rpy(_quat_slerp(default_quat, y_90_quat, y_ratio)).tolist()
    return default_rpy.tolist()
