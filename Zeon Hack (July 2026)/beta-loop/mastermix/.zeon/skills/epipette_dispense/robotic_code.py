import time

from protocol_schema import SkillObject
from utils import PRE_ASPIRATE_JOINTS, epipette_device, object_display_name

from .modules import (
    EPIPETTE_10UL,
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    epipette_dispense as _epipette_dispense_helper,
    get_world_state,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    tcp_tip_offset_from_anchors,
)

# On the way down, drop to just below the rim at medium speed before the final
# slow descent to the dispense depth (1 cm below the well top).
_RIM_APPROACH_DEPTH = 0.01  # m below the well top

# Per-pipette descent trim, in meters, added to whatever depth we resolve below.
# Escape hatch for a pipette whose tip sits lower than the shared TCP->tip model
# predicts, so it over-descends by a fixed amount on every object. Correcting it
# here keeps the object anchors and the TCP offset untouched — they stay correct
# for every other pipette. Negative = descend less deep. Applied to the final
# descent *after* depth_fraction: the tip error is a fixed distance, so trimming
# the pre-fraction depth would only correct depth_fraction of it.
DEPTH_TRIM_BY_PIPETTE = {
    "epipette_120ul": -0.004,  # yellow: bottoms out ~4 mm too deep
}


def epipette_dispense(
    object: SkillObject,
    anchor: str,
    pipette: SkillObject,
    volume: float = 5.0,
    speed: float = 5.0,
    approach_height: float = 0.15,
    dispense_depth: float = 0.0125,
    grasp_anchor: str = "grab",
    tip_anchor: str = "tip",
    tip_extension_m: float = 0.02,
    depth_top_anchor: str = "depth_top",
    depth_bottom_anchor: str = "depth_bottom",
    depth_fraction: float = 0.5,
):
    """Dispense into a well/tube anchor, with heights measured from the well top.

    By object-model convention the anchor xyz is the well/tube TOP rim, and
    ``compute_tcp_pose_from_tip_position`` handles the tip length once (the anchor
    xyz is the desired TIP position). So every vertical move is expressed as a
    signed offset from a single reference — ``well_top_z``:

      * hover    = well_top_z + approach_height         (clearance above the rim)
      * dispense = well_top_z - depth * depth_fraction  (partway into the well)
      * bottom   = well_top_z - depth                   (after dispensing; the same
                                                         low point epipette_aspirate
                                                         dips to)

    Only world Z changes, so the convention is independent of the anchor's local
    Z direction (which differs between plate families: wellplate_pcr +Z up vs
    wellplate_96_flatbottom +Z down).

    The TCP->tip offset is derived from the held pipette's own geometry rather than
    a hardcoded constant: epipette_grab snaps the TCP onto the ``grasp_anchor``, so
    the tip anchor expressed in that frame (grab^-1 @ tip), extended by
    ``tip_extension_m`` for the physical disposable tip, is where the tip sits
    relative to the hand. This is the pre-calibration estimate; the per-anchor XY
    calibration is applied on top. Falls back to the module's default offset if the
    pipette's grasp/tip anchors are unavailable.

    Args:
        object: Object to dispense into (well plate, tube rack, cold block, ...).
        anchor: Anchor name on the object model (e.g. 'A1', 'H12') = the well top.
        pipette: The pipette held by the arm (its ``grasp_anchor``/``tip_anchor``
            define where the tip is relative to the TCP).
        volume: Volume to dispense in µL.
        speed: Pipette plunger speed.
        approach_height: Hover height above the well top, in meters.
        dispense_depth: Descent below the well top before dispensing, in meters.
        grasp_anchor: Anchor on the pipette the TCP grabs at (matches epipette_grab).
        tip_anchor: Anchor at the end of the epipette (the nozzle tip).
        tip_extension_m: Length of the physical disposable tip past ``tip_anchor``,
            along the pipette axis.
        depth_fraction: Fraction of the full top->bottom depth to descend before
            dispensing. 0.5 = halfway down the well (default); 1.0 = dispense at the
            bottom. Only moves where the liquid leaves the tip — after dispensing the
            tip continues down the remaining fraction to the full depth, so a
            dispense always bottoms out at the same height as epipette_aspirate.
    """
    object_id = object.id
    anchor_name = anchor
    pipette_id = pipette.id
    pipette_name = object_display_name(pipette)

    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.8)

    # TCP->tip offset. Prefer the fixed value stored per-pipette in live_state.yaml
    # (deterministic, derived once from the pipette's object model) — resolving it
    # live from the held pipette's anchors reads the arm twice and drifts run to
    # run. Fall back to the live derivation, then the module default, if unset.
    stored = get_world_state(pipette_id).get("tcp_offset")
    if stored is not None and len(stored) == 3:
        tcp_offset = [float(v) for v in stored]
        print_log(f"epipette_dispense: TCP->tip offset {tcp_offset} from live_state (fixed)")
    else:
        try:
            grab = load_object_anchor(pipette_id, grasp_anchor)
            tip = load_object_anchor(pipette_id, tip_anchor)
            tcp_offset = tcp_tip_offset_from_anchors(grab, tip, tip_extension_m)
            print_log(
                f"epipette_dispense: TCP->tip offset {tcp_offset} from {grasp_anchor}->{tip_anchor} +{tip_extension_m}m (live; no live_state value)"
            )
        except (KeyError, ValueError) as e:
            tcp_offset = None
            print_log(
                f"epipette_dispense: pipette '{grasp_anchor}'/'{tip_anchor}' anchor unavailable ({e}); using default tip offset"
            )

    # Anchor xyz = world position of the well TOP; convert that desired TIP
    # position into the TCP pose (tip offset handled inside the helper).
    anchor_pose = load_object_anchor(object_id, anchor_name)
    orientation = compute_dispense_orientation(0, 0)
    tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(anchor_pose["xyz"], orientation, tcp_offset=tcp_offset)

    # Per-anchor XY calibration, per pipette (calibration_<pipette_name>).
    calib_key = f"calibration_{pipette_name}"
    dx, dy = get_world_state(object_id).get(calib_key, {}).get(str(anchor_name), [0.0, 0.0])
    tcp_position[0] += dx
    tcp_position[1] += dy

    # Single Z reference: the TCP height at which the tip sits at the well top.
    # Every move below is `well_top_z ± a named offset`.
    x, y = tcp_position[0], tcp_position[1]
    well_top_z = tcp_position[2]

    # Per-object descent depth — the vertical gap between two colinear anchors on the
    # object: `depth_top_anchor` (at the well/hole top) and `depth_bottom_anchor` (that
    # far below it). They share XY, so the absolute Z difference is the depth, and it
    # matches the world-Z descent below. Falls back to the fixed dispense_depth param
    # if the anchors are absent.
    try:
        top = load_object_anchor(object_id, depth_top_anchor)["xyz"]
        bot = load_object_anchor(object_id, depth_bottom_anchor)["xyz"]
        depth = abs(top[2] - bot[2])
        print_log(f"epipette_dispense: descent depth {depth:.5f} m = |{depth_top_anchor}.z - {depth_bottom_anchor}.z|")
    except (KeyError, ValueError):
        depth = dispense_depth
        print_log(f"epipette_dispense: no depth anchors; using fixed dispense_depth={dispense_depth}")

    # Dispense partway down instead of at the bottom: descend `depth_fraction` of the
    # full top->bottom depth (0.5 = halfway). Computed here, not an extra object anchor.
    # The fraction only sets where the liquid leaves the tip — after dispensing the tip
    # continues to `full_descent`, the same low point epipette_aspirate dips to, so both
    # skills bottom out at the same height on any given object.
    descent = round(depth * float(depth_fraction), 6)
    full_descent = depth
    print_log(
        f"epipette_dispense: dispensing at {depth_fraction:.2f}x depth -> {descent:.5f} m below well top "
        f"(halfway if 0.5), then continuing to the full {full_descent:.5f} m"
    )

    # Per-pipette trim (see DEPTH_TRIM_BY_PIPETTE). A fixed tip-position error, so it
    # applies to both commanded descents, post-fraction. Clamped at 0 so a trim larger
    # than a descent can never lift that move above the well top.
    trim = DEPTH_TRIM_BY_PIPETTE.get(pipette_name, 0.0)
    if trim:
        trimmed = max(0.0, round(descent + trim, 6))
        trimmed_full = max(0.0, round(full_descent + trim, 6))
        print_log(
            f"epipette_dispense: pipette '{pipette_name}' trim {trim:+.4f} m -> dispense {descent:.5f} becomes "
            f"{trimmed:.5f} m, full depth {full_descent:.5f} becomes {trimmed_full:.5f} m"
        )
        if trimmed == 0.0:
            print_log(f"epipette_dispense: WARNING trim {trim:+.4f} m >= descent {descent:.5f} m; clamped to 0 (dispensing at the well top)")
        descent, full_descent = trimmed, trimmed_full

    print_log(
        f"epipette_dispense: object_id={object_id}, anchor={anchor_name}, volume={volume}, "
        f"speed={speed}, approach_height={approach_height}, dispense_depth={dispense_depth}, "
        f"calibration=({dx},{dy})"
    )

    # 1) Hover above the well top.
    move_arm(arm="left_arm", position=[x, y, well_top_z + approach_height], orientation=tcp_orientation, speed=250)
    time.sleep(0.1)

    # 2) Descend to just below the rim at medium speed.
    move_arm(arm="left_arm", position=[x, y, well_top_z], orientation=tcp_orientation, speed=100)
    time.sleep(0.1)

    # 3) Slow descent to the (partial) dispense depth — halfway down by default.
    move_arm(arm="left_arm", position=[x, y, well_top_z - descent], orientation=tcp_orientation, speed=5)
    time.sleep(1)

    # 4) Dispense (plunger only; no arm motion).
    _epipette_dispense_helper(name=epipette_device(pipette), volume=volume, speed=speed)
    time.sleep(0.5)

    # Run log: one timestamped structured entry per dispense, with full well info
    # (print_log adds the UTC `t`, node_id, and label from the execution context).
    print_log(
        f"dispense {volume} uL into {object_display_name(object, object_id)} / well {anchor_name} "
        f"(pipette {object_display_name(pipette, pipette_id)}, speed {speed}, cal ({dx},{dy}))",
        runlog=True,
        runlog_type="dispense",
    )

    # 5) Continue down the remaining fraction to the full depth — the same low point
    # epipette_aspirate dips to. Skipped when it would not actually be lower (e.g.
    # depth_fraction >= 1, or a trim that clamped both descents to the same value),
    # so this never commands an upward "descent".
    if full_descent > descent:
        move_arm(arm="left_arm", position=[x, y, well_top_z - full_descent], orientation=tcp_orientation, speed=5)
        time.sleep(0.5)
    else:
        print_log(
            f"epipette_dispense: dispense descent {descent:.5f} m already at/below the full "
            f"{full_descent:.5f} m; no second descent"
        )

    # 6) Back up to the well top, slowly, so the tip clears the well before the fast
    # retract.
    move_arm(arm="left_arm", position=[x, y, well_top_z], orientation=tcp_orientation, speed=10)
    time.sleep(0.1)

    # 7) Retract back to the hover height.
    move_arm(arm="left_arm", position=[x, y, well_top_z + approach_height], orientation=tcp_orientation, speed=100, wait=True)
    time.sleep(0.1)

    print_log("epipette_dispense complete")
    return {"success": True}
