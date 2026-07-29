import time

from protocol_schema import SkillObject
from utils import object_display_name

from .modules import (
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    get_arm_pose,
    get_object_pose,
    get_world_state,
    move_arm,
    move_arm_js,
    print_log,
    set_world_state,
)

# Absolute world Z of the tip tops. Placeholder carried over from
# epipette_grey_attach (calibrated for pipette_demo_world) — re-calibrate for the
# active world (e.g. hack_world_21) in sim.
# TIP_HEIGHT = 0.065
TIP_HEIGHT = 0.045

# Fixed nozzle-down orientation over the rack (left arm), shared with epipette_grey_attach.
ARM_ORIENTATION = [-0.977, -1.555, -2.200]

# Staging joint pose over the tip rack (left arm).
ATTACH_JOINTS = [0.893, 0.354, -1.207, -0.881, 2.177, 2.538]


def epipette_attach(tipbox: SkillObject, pipette: SkillObject, tip_index: int = 1):
    """Attach a single rack tip to the held pipette — calibration-file mock of epipette_grey_attach.

    Unlike the anchor-driven attach, this positions the tip exactly like
    epipette_grey_attach: no anchors. The tip XY is the ``tipbox``'s world pose
    (``get_object_pose``) plus the per-tip ``[dx, dy]`` offset stored in the box's
    live state. Calibration is kept **per pipette**: the attaching pipette's world
    name selects the table, ``calibration_<pipette_name>`` (e.g.
    ``calibration_epipette_10ul`` / ``calibration_epipette_120ul``), keyed by
    ``str(tip_index)``. Z is the absolute module constant ``TIP_HEIGHT``. It presses
    the pipette nozzle straight down onto that one tip at a fixed arm orientation,
    then lifts.

    Minimal on purpose: the caller picks which box and tip. No tipbox registry, no
    active-rack logic, no ``tip_index`` advancement, and no laser tip-check/retry
    loop (that hardware verification is what this mocks out).

    Args:
        tipbox: The tip rack to attach from.
        tip_index: 1-based tip to use; selects the ``calibration_<pipette_name>`` entry str(tip_index).
    """

    print_log(runlog=True, runlog_type="step_start")
    tipbox_id = tipbox.id
    tipbox_name = object_display_name(tipbox)
    pipette_id = pipette.id
    pipette_name = object_display_name(pipette)

    # Calibration is stored per pipette: the attaching pipette's world name selects
    # which per-tip [dx, dy] table to read (e.g. "calibration_epipette_10ul").
    calib_key = f"calibration_{pipette_name}" if pipette_name else "calibration"
    print_log(
        f"Starting epipette_attach (tipbox={tipbox_name or tipbox_id}, tip_index={tip_index}, pipette={pipette_name or pipette_id}, calib_key={calib_key})"
    )

    move_arm_js(arm="left_arm", joint_angles=ATTACH_JOINTS, speed=1)

    # Fixed TCP->tip offset read from the pipette's live_state (the same value
    # epipette_aspirate uses) — never computed live. If unset, tcp_offset stays None
    # and compute_tcp_pose_from_tip_position falls back to the module default constant.
    stored = get_world_state(pipette_id).get("tcp_offset")
    tcp_offset = [float(v) for v in stored] if (stored is not None and len(stored) == 3) else None

    # Tip target: calibration-file XY (tipbox pose + per-tip offset) + absolute TIP_HEIGHT Z.
    # The per-tip offset comes from the box's per-pipette calibration table (calib_key).
    tipbox_pose = get_object_pose(tipbox_name)
    # ``or {}`` guards an empty/None calibration table (a bare "calibration_<pipette>:"
    # in live_state parses to None) — fall back to a zero [dx, dy] offset.
    dx, dy = (get_world_state(tipbox_id).get(calib_key) or {}).get(str(tip_index), [0.0, 0.0])
    tip_target = [tipbox_pose["xyz"][0] + dx, tipbox_pose["xyz"][1] + dy, TIP_HEIGHT]

    # Convert the desired tip position to a TCP pose using the stored offset, exactly
    # like epipette_aspirate. ref_z is that Z value — the TCP height at which the tip
    # sits at the absolute TIP_HEIGHT.
    orientation = compute_dispense_orientation(0, 0)
    tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(tip_target, orientation, tcp_offset=tcp_offset)
    x, y, ref_z = tcp_position[0], tcp_position[1], tcp_position[2]
    print_log(f"epipette_attach: tip {tip_index} target {tip_target} -> TCP z {ref_z}; offset {tcp_offset} (dx={dx}, dy={dy})")
    attach_orientation = ARM_ORIENTATION  ## TEMPORARY: CHANGE TO ORIENTATION OF TIP RACK

    # Per-pipette attach depths (descend, press, settle, lift) from the tipbox live state.
    depths_key = f"attach_depths_{pipette_name}"
    attach_depths = get_world_state(tipbox_id).get(depths_key)
    print_log(f"epipette_attach: {depths_key} = {attach_depths}")

    # Descend close to the tip top.
    move_arm(arm="left_arm", position=[x, y, ref_z + attach_depths[0]], orientation=attach_orientation, speed=60)

    # Press down onto the tip.
    move_arm(arm="left_arm", position=[x, y, ref_z + attach_depths[1]], orientation=attach_orientation, speed=10)
    time.sleep(0.1)

    # Settle.
    move_arm(arm="left_arm", position=[x, y, ref_z + attach_depths[2]], orientation=attach_orientation, speed=8)
    time.sleep(0.1)

    # Lift off with the tip attached.
    move_arm(arm="left_arm", position=[x, y, ref_z + attach_depths[3]], orientation=attach_orientation, speed=100)
    time.sleep(0.1)

    move_arm_js(arm="left_arm", joint_angles=ATTACH_JOINTS, speed=1)

    # set_world_state(tipbox_id, {"tip_index": tip_index + 1})

    print_log("epipette_attach complete")
    return {"success": True}
