import time

from protocol_schema import SkillObject
from utils import PRE_ASPIRATE_JOINTS, epipette_device_name, object_display_name

from .modules import (
    compute_dispense_orientation,
    compute_tcp_pose_from_tip_position,
    epipette_aspirate as _epipette_aspirate_helper,
    get_world_state,
    load_object_anchor,
    move_arm,
    move_arm_js,
    print_log,
    tcp_tip_offset_from_anchors,
)

# On the way down, drop to just below the rim at medium speed before the final
# slow dip. Kept as the previous skill's intermediate standoff (1 cm below top).


def epipette_aspirate(
    object: SkillObject,
    anchor: str,
    pipette: SkillObject,
    volume: float = 5.0,
    speed: float = 5.0,
    approach_height: float = 0.15,
    aspirate_depth: float = 0.002,
    use_calibration: bool = True,
    grasp_anchor: str = "grab",
    tip_anchor: str = "tip",
    tip_extension_m: float = 0.02,
    depth_top_anchor: str = "depth_top",
    depth_bottom_anchor: str = "depth_bottom",
):
    """Aspirate from a well/tube anchor, with heights measured from the well top.

    By object-model convention the anchor xyz is the well/tube TOP rim, and
    ``compute_tcp_pose_from_tip_position`` handles the tip length once (the anchor
    xyz is the desired TIP position). So every vertical move is expressed as a
    signed offset from a single reference — ``well_top_z`` — instead of magic
    numbers layered on an opaque base:

      * hover   = well_top_z + approach_height   (clearance above the rim)
      * dip     = well_top_z - aspirate_depth    (into the liquid)

    Only world Z changes, so the convention is independent of the anchor's local
    Z direction (which differs between plate families: wellplate_pcr +Z up vs
    wellplate_96_flatbottom +Z down).

    The TCP->tip offset is read from the fixed ``tcp_offset`` stored per-pipette in
    ``live_state.yaml`` (a constant derived once from the pipette's object model:
    grab^-1 @ tip, extended by the physical disposable tip). Resolving it live from
    the held pipette's anchors reads the arm twice and drifts run to run, so the
    stored value is preferred; if it is absent the skill falls back to the live
    ``grasp_anchor``->``tip_anchor`` derivation, then to the module's default. This
    is the pre-calibration estimate; the optional per-anchor XY calibration is
    applied on top.

    Args:
        object: Object to aspirate from (well plate, tube rack, cold block, ...).
        anchor: Anchor name on the object model (e.g. 'A1', 'H12') = the well top.
        pipette: The pipette held by the arm (its ``grasp_anchor``/``tip_anchor``
            define where the tip is relative to the TCP).
        volume: Volume to aspirate in µL.
        speed: Pipette plunger speed.
        approach_height: Hover height above the well top, in meters.
        aspirate_depth: Descent below the well top into the liquid, in meters.
        use_calibration: Apply the stored per-anchor XY calibration offset.
        grasp_anchor: Anchor on the pipette the TCP grabs at (matches epipette_grab).
        tip_anchor: Anchor at the end of the epipette (the nozzle tip).
        tip_extension_m: Length of the physical disposable tip past ``tip_anchor``,
            along the pipette axis.
    """
    object_id = object.id
    anchor_name = anchor
    pipette_id = pipette.id
    pipette_name = object_display_name(pipette)
    # Which physical plunger to drive — derived from the bound pipette, not
    # hardcoded, so the same skill serves the 10 uL and the 120 uL pipette.
    device = epipette_device_name(pipette)

    move_arm_js(arm="left_arm", joint_angles=PRE_ASPIRATE_JOINTS, speed=0.8)

    # TCP->tip offset. Prefer the fixed value stored per-pipette in live_state.yaml
    # (deterministic, derived once from the pipette's object model) — resolving it
    # live from the held pipette's anchors reads the arm twice and drifts run to
    # run. Fall back to the live derivation, then the module default, if unset.
    stored = get_world_state(pipette_id).get("tcp_offset")
    if stored is not None and len(stored) == 3:
        tcp_offset = [float(v) for v in stored]
        print_log(f"epipette_aspirate: TCP->tip offset {tcp_offset} from live_state (fixed)")
    else:
        try:
            grab = load_object_anchor(pipette_id, grasp_anchor)
            tip = load_object_anchor(pipette_id, tip_anchor)
            tcp_offset = tcp_tip_offset_from_anchors(grab, tip, tip_extension_m)
            print_log(
                f"epipette_aspirate: TCP->tip offset {tcp_offset} from {grasp_anchor}->{tip_anchor} +{tip_extension_m}m (live; no live_state value)"
            )
        except (KeyError, ValueError) as e:
            tcp_offset = None
            print_log(
                f"epipette_aspirate: pipette '{grasp_anchor}'/'{tip_anchor}' anchor unavailable ({e}); using default tip offset"
            )

    # Anchor xyz = world position of the well TOP; convert that desired TIP
    # position into the TCP pose (tip offset handled inside the helper).
    anchor_pose = load_object_anchor(object_id, anchor_name)
    orientation = compute_dispense_orientation(0, 0)
    tcp_position, tcp_orientation = compute_tcp_pose_from_tip_position(anchor_pose["xyz"], orientation, tcp_offset=tcp_offset)

    # Optional per-anchor XY calibration, per pipette (calibration_<pipette_name>).
    if use_calibration:
        calib_key = f"calibration_{pipette_name}"
        dx, dy = get_world_state(object_id).get(calib_key, {}).get(str(anchor_name), [0.0, 0.0])
        tcp_position[0] += dx
        tcp_position[1] += dy
    else:
        dx, dy = 0.0, 0.0

    # Single Z reference: the TCP height at which the tip sits at the well top.
    # Every move below is `well_top_z ± a named offset`.
    x, y = tcp_position[0], tcp_position[1]
    well_top_z = tcp_position[2]

    # Per-object descent depth — the vertical gap between two colinear anchors on the
    # object: `depth_top_anchor` (at the well/hole top) and `depth_bottom_anchor` (that
    # far below it). They share XY, so the absolute Z difference is the depth, and it
    # matches the world-Z descent below. Falls back to the fixed aspirate_depth param
    # if the anchors are absent.
    try:
        top = load_object_anchor(object_id, depth_top_anchor)["xyz"]
        bot = load_object_anchor(object_id, depth_bottom_anchor)["xyz"]
        depth = abs(top[2] - bot[2])
        print_log(f"epipette_aspirate: descent depth {depth:.5f} m = |{depth_top_anchor}.z - {depth_bottom_anchor}.z|")
    except (KeyError, ValueError):
        depth = aspirate_depth
        print_log(f"epipette_aspirate: no depth anchors; using fixed aspirate_depth={aspirate_depth}")

    print_log(f"WELL: {anchor_name}, epipette_aspirate: tcp_position={tcp_position}, tcp_orientation={tcp_orientation}")

    print_log(
        f"epipette_aspirate: object_id={object_id}, anchor={anchor_name}, volume={volume}, "
        f"speed={speed}, approach_height={approach_height}, aspirate_depth={aspirate_depth}, "
        f"calibration=({dx},{dy})"
    )

    # 1) Hover above the well top.
    move_arm(arm="left_arm", position=[x, y, well_top_z + approach_height], orientation=tcp_orientation, speed=250)
    time.sleep(0.1)

    # 2) Descend to just below the rim at medium speed.
    move_arm(arm="left_arm", position=[x, y, well_top_z], orientation=tcp_orientation, speed=50)
    time.sleep(0.1)

    # 3) Slow dip into the liquid.
    move_arm(arm="left_arm", position=[x, y, well_top_z - depth], orientation=tcp_orientation, speed=5)
    time.sleep(1)

    # 4) Aspirate (plunger only; no arm motion).
    _epipette_aspirate_helper(name=device, volume=volume, speed=speed)
    time.sleep(0.5)

    # 5) Retract back to the hover height.
    move_arm(arm="left_arm", position=[x, y, well_top_z + approach_height], orientation=tcp_orientation, speed=100, wait=True)
    time.sleep(0.1)

    print_log("epipette_aspirate complete")
    return {"success": True}
