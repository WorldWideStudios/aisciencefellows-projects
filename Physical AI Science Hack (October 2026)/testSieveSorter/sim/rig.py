"""BioKEA's BugSorter tower, drawn around a holder-box run on the replay page (viewer.py --rig bugsorter).
Display only: none of it is in the physics, and it stays still while the trays move.

What it shows: a black aluminium-extrusion frame standing in a white water tub (the team's photo of the
bench unit, 2026-10-25); each holder box on a pivot axle across its middle, carried by a post on each
side, with a knob on the front (docs/SYSTEM.md section 3, confirmed by the user at 10:50: each tray
seesaws about its own pivot across its middle, ends tipping); a hex-perforated spray plate over the top
box; the M5Stack controller on a plate across the top; clear acrylic panels round the back and the ends.

The pivots come from the run when it has them (scene["levels"][k]["pivot"], a seesaw run); otherwise
each holder box's centre. The corner uprights stand clear of a box's corners at any tilt. Every size
below is ESTIMATED from the photo, scaled by the 140 x 104 x 25 mm holder box; measure the bench unit
and change them here. The level spacing is the run's own: SYSTEM.md asks for 80-100 mm for a +/-25 deg
seesaw with neighbours in opposite phase.
"""
import math

EXTRUSION = 20.0              # square aluminium extrusion
FRAME_Y = 72.0                # extrusion centre lines at y = +/- this (the box is 104 wide)
SWEEP_CLEAR = 8.0             # the corner uprights clear a box's corners at any tilt by this much
AXLE_D, KNOB_D, KNOB_L = 6.0, 20.0, 10.0
KNOB_SIDE = 1                 # knobs on the +Y side, the side the photo is taken from
SPRAY_ABOVE = 50.0            # spray plate above the top box's rim
SPRAY_L, SPRAY_W, SPRAY_T = 120.0, 100.0, 2.0
HEX_PITCH, HEX_D = 9.0, 5.0   # spray plate holes, on a hexagonal grid
TOP_ABOVE = 110.0             # top of the frame above the top box's rim
TOP_PLATE_T = 5.0
TUB_L, TUB_W, TUB_DEPTH, TUB_WALL = 400.0, 280.0, 120.0, 3.0
TUB_RIM_BELOW = 40.0          # tub rim below the bottom box, clear of its tipping ends
WATER = 70.0                  # water depth in the tub
ACRYLIC_T, ACRYLIC_GAP = 4.0, 30.0

BLACK = [0.09, 0.09, 0.10, 1.0]
STEEL = [0.55, 0.57, 0.60, 1.0]
KNOB = [0.42, 0.44, 0.47, 1.0]
WHITE = [0.95, 0.95, 0.93, 1.0]
SPRAY = [0.86, 0.87, 0.89, 1.0]
HOLE = [0.20, 0.21, 0.24, 1.0]
TUB = [0.97, 0.97, 0.97, 0.45]
WATER_RGBA = [0.55, 0.74, 0.95, 0.22]
ACRYLIC = [0.85, 0.92, 1.0, 0.07]
_S = math.sqrt(0.5)
AXIS_QUAT = {"x": [_S, 0.0, _S, 0.0], "y": [_S, -_S, 0.0, 0.0], "z": [1.0, 0.0, 0.0, 0.0]}   # local z onto x, y, z


def box(x0, x1, y0, y1, z0, z1, rgba, part):
    return {"type": "box", "size": [(x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2],
            "pos": [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], "quat": [1.0, 0.0, 0.0, 0.0],
            "rgba": rgba, "role": "rig", "part": part}


def cylinder(axis, a0, a1, centre, r, rgba, part):
    """Along `axis` from a0 to a1; centre gives the other two coordinates (and is overwritten on the axis)."""
    pos = list(centre)
    pos["xyz".index(axis)] = (a0 + a1) / 2
    return {"type": "cylinder", "size": [r, abs(a1 - a0) / 2], "pos": pos, "quat": AXIS_QUAT[axis],
            "rgba": rgba, "role": "rig", "part": part}


def holders(tray_geoms):
    """The holder boxes, bottom first, as (x_free, x_body_end, x_tab_end, z0, z1): each holder's +X tab is
    a box reaching furthest along +X, as tall as the holder."""
    boxes = [g for g in tray_geoms if g["type"] == "box" and g.get("role") != "lid"]
    x_end = max(g["pos"][0] + g["size"][0] for g in boxes)
    x_free = min(g["pos"][0] - g["size"][0] for g in boxes)
    tabs = [g for g in boxes if abs(g["pos"][0] + g["size"][0] - x_end) < 1e-6]
    return sorted((x_free, g["pos"][0] - g["size"][0], x_end, g["pos"][2] - g["size"][2], g["pos"][2] + g["size"][2])
                  for g in tabs)


def bugsorter(scene):
    """The tower around scene["tray"]: a list of display-only geoms in the lab frame (the trays level)."""
    tray = [g for g in scene["tray"]["geoms"] if g.get("role") != "lid"]
    levels = [h[3:] for h in holders(tray)]
    x_free, x_body, x_end = holders(tray)[0][:3]
    run_pivots = [lv["pivot"] for lv in scene.get("levels", []) if lv.get("pivot")]
    if run_pivots:
        pivots = sorted(run_pivots, key=lambda p: p[2])
    else:
        pivots = [[(x_free + x_body) / 2, 0.0, (z0 + z1) / 2] for z0, z1 in levels]
    xc = pivots[0][0]
    reach = max(math.hypot(x - xc, z - p[2]) for p, (z0, z1) in zip(pivots, levels)
                for x in (x_free, x_end) for z in (z0, z1))
    xr, xl = xc + reach + SWEEP_CLEAR + EXTRUSION / 2, xc - reach - SWEEP_CLEAR - EXTRUSION / 2
    e = EXTRUSION / 2
    z_rim = levels[-1][1]                                     # top box's rim
    z_floor = levels[0][0] - TUB_RIM_BELOW - TUB_DEPTH
    z_top = z_rim + TOP_ABOVE
    g = []
    # frame: four corner uprights standing on the tub floor, two pivot posts, rails round the top, a plate
    for x in (xl, xr):
        for y in (-FRAME_Y, FRAME_Y):
            g.append(box(x - e, x + e, y - e, y + e, z_floor + TUB_WALL, z_top, BLACK, "frame"))
    for y in (-FRAME_Y, FRAME_Y):
        g.append(box(xc - e, xc + e, y - e, y + e, z_floor + TUB_WALL, z_top - EXTRUSION, BLACK, "pivot post"))
        g.append(box(xl + e, xr - e, y - e, y + e, z_top - EXTRUSION, z_top, BLACK, "frame"))
    for x in (xl, xr):
        g.append(box(x - e, x + e, -FRAME_Y + e, FRAME_Y - e, z_top - EXTRUSION, z_top, BLACK, "frame"))
    g.append(box(xc - 45, xc + 85, -FRAME_Y - e, FRAME_Y + e, z_top, z_top + TOP_PLATE_T, BLACK, "top plate"))
    # controller: printed mount and the M5Stack Core on top
    zc = z_top + TOP_PLATE_T
    g.append(box(xc - 10, xc + 65, -30, 30, zc, zc + 28, WHITE, "controller mount"))
    g.append(box(xc + 1, xc + 55, -27, 27, zc + 28, zc + 45, BLACK, "controller"))
    # each tray on a pivot axle across its middle: stubs from its long walls to the posts, knob on the front
    half_w = max(abs(gm["pos"][1]) + gm["size"][1] for gm in tray if gm["type"] == "box")
    y_out = FRAME_Y + e
    for px, _, pz in pivots:
        for sy in (-1, 1):
            g.append(cylinder("y", sy * half_w, sy * y_out, (px, 0, pz), AXLE_D / 2, STEEL, "pivot axle"))
        ky = KNOB_SIDE * (y_out + KNOB_L / 2)
        g.append(cylinder("y", ky - KNOB_L / 2, ky + KNOB_L / 2, (px, 0, pz), KNOB_D / 2, KNOB, "knob"))
    # spray plate over the top box, hung from the top rails, holes on a hex grid
    zs = z_rim + SPRAY_ABOVE
    sx = (x_free + x_body) / 2
    g.append(box(sx - SPRAY_L / 2, sx + SPRAY_L / 2, -SPRAY_W / 2, SPRAY_W / 2, zs, zs + SPRAY_T, SPRAY, "spray plate"))
    for x in (sx - SPRAY_L / 2 + 6, sx + SPRAY_L / 2 - 6):
        g.append(cylinder("z", zs + SPRAY_T, z_top - EXTRUSION, (x, 0, 0), 2.0, STEEL, "spray hanger"))
    row_h = HEX_PITCH * math.sqrt(3) / 2
    for j in range(int((SPRAY_W - HEX_PITCH) // row_h) + 1):
        y = -SPRAY_W / 2 + HEX_PITCH / 2 + j * row_h
        x0 = sx - SPRAY_L / 2 + HEX_PITCH / 2 + (HEX_PITCH / 2 if j % 2 else 0)
        while x0 <= sx + SPRAY_L / 2 - HEX_PITCH / 2 + 1e-6:
            g.append(cylinder("z", zs - 0.1, zs + SPRAY_T + 0.1, (x0, y, 0), HEX_D / 2, HOLE, "spray hole"))
            x0 += HEX_PITCH
    # the tub, with water in it
    tx, ty = TUB_L / 2, TUB_W / 2
    z_rim_tub = z_floor + TUB_DEPTH
    g.append(box(xc - tx, xc + tx, -ty, ty, z_floor, z_floor + TUB_WALL, TUB, "tub"))
    for sy in (-1, 1):
        y0 = sy * ty - TUB_WALL if sy > 0 else -ty
        g.append(box(xc - tx, xc + tx, y0, y0 + TUB_WALL, z_floor, z_rim_tub, TUB, "tub"))
    for sx_ in (-1, 1):
        x0 = xc + sx_ * tx - TUB_WALL if sx_ > 0 else xc - tx
        g.append(box(x0, x0 + TUB_WALL, -ty + TUB_WALL, ty - TUB_WALL, z_floor, z_rim_tub, TUB, "tub"))
    g.append(box(xc - tx + TUB_WALL, xc + tx - TUB_WALL, -ty + TUB_WALL, ty - TUB_WALL, z_floor + TUB_WALL,
                 z_floor + TUB_WALL + WATER, WATER_RGBA, "water"))
    # acrylic: behind the frame (away from the knobs) and at both ends
    yb = -KNOB_SIDE * (FRAME_Y + e + ACRYLIC_GAP)
    xa = (xr - xl) / 2 + e + ACRYLIC_GAP
    g.append(box(xc - xa, xc + xa, yb - ACRYLIC_T / 2, yb + ACRYLIC_T / 2, z_rim_tub, z_top + 20, ACRYLIC, "acrylic"))
    y0, y1 = sorted((yb, KNOB_SIDE * (FRAME_Y + e)))        # from the back panel to the front of the frame
    for sx_ in (-1, 1):
        x = xc + sx_ * xa
        g.append(box(x - ACRYLIC_T / 2, x + ACRYLIC_T / 2, y0, y1, z_rim_tub, z_top + 20, ACRYLIC, "acrylic"))
    return g
