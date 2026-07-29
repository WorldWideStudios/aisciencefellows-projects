import time

from protocol_schema import SkillObject
from utils import object_display_name

from .modules import (
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    get_object_pose,
    get_world_state,
    move_arm,
    move_arm_js,
    print_log,
    set_world_state,
)

# Tips per rack. The box's live_state `tip_index` counts 1..TIP_COUNT.
TIP_COUNT = 96

# Absolute world Z of the tip tops, calibrated for pipette_demo_world.
# Re-measure it in sim if you re-export the deck at a different height.
TIP_HEIGHT = 0.045

# Fixed nozzle-down orientation over the rack (left arm).
ARM_ORIENTATION = [-0.977, -1.555, -2.200]

# Staging joint pose over the tip rack (left arm). A task pose, not a
# transition pose — it is tied to where the racks sit on this deck. Relocate
# via the transition poses in utils.py; land here only to work the rack.
ATTACH_JOINTS = [0.893, 0.354, -1.207, -0.881, 2.177, 2.538]

# Descend / press / settle / lift offsets relative to the TCP height at which the
# tip sits at TIP_HEIGHT. Per-box, per-pipette values live in the tip box's
# live_state under ``attach_depths_<pipette_name>``; this is the fallback when a
# box carries no entry for the pipette being used.
DEFAULT_ATTACH_DEPTHS = [0.04, -0.01, -0.0207, 0.1]


def epipette_attach(tipbox: SkillObject, pipette: SkillObject, tip_index: int = 0):
    """Press the held pipette onto one rack tip to latch it.

    Calibration-table driven rather than anchor driven: a tip box has 96 tips
    that a single object anchor can't address, so the tip XY is the ``tipbox``'s
    world pose (``get_object_pose``) plus the per-tip ``[dx, dy]`` offset stored
    in the box's live state. Calibration is kept **per pipette** — the attaching
    pipette's world name selects the table ``calibration_<pipette_name>`` (e.g.
    ``calibration_epipette_10ul`` / ``calibration_epipette_120ul``), keyed by
    ``str(tip_index)``. Z is the absolute module constant ``TIP_HEIGHT``. The
    nozzle then presses straight down onto that one tip at a fixed arm
    orientation and lifts off with the tip attached.

    **Tip cycling.** With the default ``tip_index=0`` the skill consumes the
    box's own ``tip_index`` counter from ``live_state.yaml`` and advances it, so
    repeated runs walk the rack (1, 2, 3, …) instead of stabbing the same tip.
    The counter is the shared source of truth — the canvas reads it to show
    remaining tips. Passing an explicit 1..96 is a manual override for that one
    attach and deliberately leaves the counter untouched.

    No verification that a tip actually latched — this is open loop.

    Args:
        tipbox: The tip rack to attach from.
        pipette: The pipette held by the arm; its world name selects the
            per-pipette calibration and attach-depth tables on the box.
        tip_index: 1-based tip to use, selecting the ``calibration_<pipette_name>``
            entry ``str(tip_index)``. Leave at 0 to take (and advance) the box's
            next-tip counter.

    Raises:
        ValueError: if the rack is exhausted, or an explicit ``tip_index`` is
            outside 1..96. Reset ``tip_index`` in ``live_state.yaml`` (or bind a
            fresh box) to continue.
    """

    print_log(runlog=True, runlog_type="step_start")
    tipbox_id = tipbox.id
    tipbox_name = object_display_name(tipbox)
    pipette_id = pipette.id
    pipette_name = object_display_name(pipette)
    box_label = tipbox_name or tipbox_id

    # Calibration is stored per pipette: the attaching pipette's world name selects
    # which per-tip [dx, dy] table to read (e.g. "calibration_epipette_10ul").
    calib_key = f"calibration_{pipette_name}" if pipette_name else "calibration"

    # Resolve which tip to take. tip_index=0 means "whatever the box says is next";
    # anything else is an explicit override that must still be a real tip.
    auto_cycle = not tip_index
    if auto_cycle:
        tip_index = int(get_world_state(tipbox_id).get("tip_index", 1))
        if not 1 <= tip_index <= TIP_COUNT:
            raise ValueError(
                f"tip rack {box_label} is exhausted (tip_index={tip_index} of {TIP_COUNT}); "
                f"reset tip_index in live_state.yaml or bind a fresh box"
            )
    elif not 1 <= tip_index <= TIP_COUNT:
        raise ValueError(f"tip_index must be 1..{TIP_COUNT} (got {tip_index})")

    print_log(
        f"Starting epipette_attach (tipbox={box_label}, tip_index={tip_index}"
        f"{' [auto]' if auto_cycle else ' [explicit]'}, pipette={pipette_name or pipette_id}, calib_key={calib_key})"
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
    dx, dy = get_world_state(tipbox_id).get(calib_key, {}).get(str(tip_index), [0.0, 0.0])
    tip_target = [tipbox_pose["xyz"][0] + dx, tipbox_pose["xyz"][1] + dy, TIP_HEIGHT]

    # Convert the desired tip position to a TCP pose using the stored offset, exactly
    # like epipette_aspirate. ref_z is that Z value — the TCP height at which the tip
    # sits at the absolute TIP_HEIGHT.
    orientation = compute_dispense_orientation(0, 0)
    tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(tip_target, orientation, tcp_offset=tcp_offset)
    x, y, ref_z = tcp_position[0], tcp_position[1], tcp_position[2]
    print_log(f"epipette_attach: tip {tip_index} target {tip_target} -> TCP z {ref_z}; offset {tcp_offset} (dx={dx}, dy={dy})")
    attach_orientation = ARM_ORIENTATION

    # Per-pipette attach depths (descend, press, settle, lift) from the tipbox live
    # state. A box that carries no table for this pipette falls back to the module
    # default rather than crashing mid-descent on a missing key.
    depths_key = f"attach_depths_{pipette_name}"
    attach_depths = get_world_state(tipbox_id).get(depths_key)
    if not attach_depths or len(attach_depths) != 4:
        print_log(
            f"epipette_attach: no usable {depths_key} on {tipbox_name or tipbox_id}; "
            f"using DEFAULT_ATTACH_DEPTHS {DEFAULT_ATTACH_DEPTHS}"
        )
        attach_depths = DEFAULT_ATTACH_DEPTHS
    else:
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

    # Burn the tip: advance the box's counter so the next auto attach takes the
    # next one. Only when the counter was the source — an explicit tip_index is a
    # one-off override and must not move the shared pointer. Writing tip_index
    # also republishes the tip-box counts to the canvas. Runs past the last tip
    # leave the counter at TIP_COUNT + 1, which is what raises "exhausted" above
    # rather than silently wrapping onto used tips.
    if auto_cycle:
        set_world_state(tipbox_id, {"tip_index": tip_index + 1})
        remaining = TIP_COUNT - tip_index
        print_log(f"epipette_attach: consumed tip {tip_index} of {box_label}; {remaining} left")

    print_log("epipette_attach complete")
    return {"success": True, "tip_index": tip_index, "tipbox": box_label}
