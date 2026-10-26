"""Printable sorting hardware (parametric CSG with manifold3d -> STL). All dimensions in mm.

Trommel (rotary drum sifter), hand-crank demo:
  three swappable drum ZONES with hole size increasing toward the exit (fines fall first, each zone
  drops its size class into its own bin, oversize leaves the open exit end): one drum replaces a
  stack of trays. Zones key together with spigots, so sizes can be reordered or replaced.
  Inlet/outlet caps with spoked hubs on an 8 mm rod, two stands with 608 bearing pockets (3 deg
  incline), a hand crank, and a crank whose knob has parallel flats so the robot arm can turn it.
  Low internal lifter ribs tumble gently (no blades).
Bins: one per zone, ArUco/AprilTag pocket on the front face (camera scale + identity, as in the
  image-sizing papers) and M3 holes for the arm grip handle.
Vortexer kit: puck for a 3 in (76 mm) vortex platform + stackable 50 mm mini sieve rings + pan + lid,
  rubber-band hooks to hold the stack.
Slow-centrifuge kit: insect strainer cup that sits in the mouth of a 50 mL conical tube.
Arm grip handle: parallel jaw flats with V-grooves (self-centring), tag pocket, 2 x M3 base.

These are geometry concepts for visual review: printability, fit to your vortexer/centrifuge/arm and
specimen safety are untested. Printed holes are not calibrated apertures (measure them).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from manifold3d import Manifold, OpType

SEG = 48
P = {  # every dimension in one place
    "drum_od": 110.0, "drum_wall": 2.4, "zone_len": 70.0, "spigot_len": 6.0, "fit": 0.25,
    "zone_holes": [2.0, 4.0, 7.0], "hole_web": 1.6, "rib_h": 2.5, "rib_w": 2.0, "n_ribs": 3,
    "rod_d": 8.0, "bearing_od": 22.0, "bearing_w": 7.0, "incline_deg": 3.0, "axis_h": 105.0,
    "jaw_gap": 20.0, "vortex_platform_d": 76.0, "mini_od": 50.0, "mini_h": 15.0, "mini_holes": [1.5, 3.0, 5.0],
    "tube_id": 27.0, "tube_holes": [1.5, 3.0], "tag": 25.0, "m3": 3.2, "m3_pilot": 2.6,
}


def cyl(h, r, r2=None, seg=SEG, center=False):
    return Manifold.cylinder(h, r, r if r2 is None else r2, seg, center)


def box(x, y, z, center=False):
    return Manifold.cube([x, y, z], center)


def tube(h, ro, ri, seg=SEG):
    return cyl(h, ro, seg=seg) - cyl(h + 2, ri, seg=seg).translate([0, 0, -1])


def union(parts):
    return Manifold.batch_boolean(parts, OpType.Add)


def radial_holes(od, wall, z0, z1, d, web, skip_angles=(), skip_half_deg=0.0, seg=16):
    """Radial cylinders through a tube wall (tube axis = z), staggered rings."""
    pitch = d + web
    n = max(3, int(math.pi * od / pitch))
    holes, k = [], 0
    z = z0 + d / 2
    while z <= z1 - d / 2:
        off = (k % 2) * 180.0 / n
        for i in range(n):
            a = i * 360.0 / n + off
            if any(abs((a - s + 180) % 360 - 180) < skip_half_deg for s in skip_angles):
                continue
            holes.append(cyl(wall + 6, d / 2, seg=seg).translate([0, 0, -(wall + 6) / 2 + od / 2 - wall / 2])
                         .rotate([0, 90, 0]).rotate([0, 0, a]).translate([0, 0, z]))
        z += pitch * math.sqrt(3) / 2; k += 1
    return holes


# ------------------------------------------------------------------ trommel
def drum_zone(hole_d):
    od, w, L, s, fit = P["drum_od"], P["drum_wall"], P["zone_len"], P["spigot_len"], P["fit"]
    ri = od / 2 - w
    body = tube(L, od / 2, ri, seg=96)
    spigot = tube(s, ri - fit, ri - fit - 2.2, seg=96).translate([0, 0, L])
    ang = [i * 360 / P["n_ribs"] for i in range(P["n_ribs"])]
    ribs = [box(P["rib_h"] + 1, P["rib_w"], L - 4).translate([ri - P["rib_h"], -P["rib_w"] / 2, 2]).rotate([0, 0, a]) for a in ang]
    half = math.degrees((P["rib_w"] / 2 + hole_d / 2 + 0.8) / ri)
    band = P.get("hole_band")          # perforate only a centred band so fines land inside the tray under this zone
    z0, z1 = ((L - band) / 2, (L + band) / 2) if band else (4, L - 4)
    holes = radial_holes(od, w, z0, z1, hole_d, P["hole_web"], ang, half)
    return union([body, spigot] + ribs) - union(holes)


def drum_cap(kind):
    """kind 'inlet' fits the plain (female) end of zone 1; 'outlet' fits the spigot of the last zone."""
    od, w, s, fit = P["drum_od"], P["drum_wall"], P["spigot_len"], P["fit"]
    ri = od / 2 - w
    flange = tube(3, od / 2 + 2, 35, seg=96)
    if kind == "inlet":
        joint = tube(s, ri - fit, ri - fit - 2.2, seg=96).translate([0, 0, 3])
    else:
        joint = tube(s, od / 2 + 2, ri - fit - 2.2 + fit * 2 + 2.2 + 0.0, seg=96).translate([0, 0, 3])
    hub = tube(22, 11, P["rod_d"] / 2 + 0.2).translate([0, 0, -8])
    spokes = [box(36, 6, 3).translate([0, -3, 0]).rotate([0, 0, a]) for a in (90, 210, 330)]
    setscrew = cyl(12, P["m3_pilot"] / 2, seg=16).rotate([0, 90, 0]).translate([4, 0, -2])
    return union([flange, joint, hub] + spokes) - setscrew


def stand(height_extra=0.0):
    h = P["axis_h"] + height_extra
    foot = box(90, 60, 5).translate([-45, -30, 0])
    post = box(26, 10, h + 14).translate([-13, -5, 0])
    boss = cyl(10, 17).rotate([90, 0, 0]).translate([0, 5, h])
    gussets = [Manifold.hull(union([box(2, 10, 30).translate([sx * 13 - (2 if sx > 0 else 0), -5, 5]),
                                    box(2, 10, 1).translate([sx * 40 - (2 if sx > 0 else 0), -5, 5])])) for sx in (-1, 1)]
    bearing = cyl(P["bearing_w"] + 0.4, P["bearing_od"] / 2 + 0.15).rotate([90, 0, 0]).translate([0, 5.01, h])
    rod = cyl(30, P["rod_d"] / 2 + 1.0).rotate([90, 0, 0]).translate([0, 15, h])
    screws = [cyl(10, P["m3"] / 2, seg=16).translate([x, y, -1]) for x in (-35, 35) for y in (-20, 20)]
    return union([foot, post, boss] + gussets) - union([bearing, rod] + screws)


def crank(arm_knob=False):
    hub = tube(14, 11, P["rod_d"] / 2 + 0.2)
    arm = box(60, 14, 7).translate([0, -7, 0])
    knob_r = 7.0
    if arm_knob:   # parallel flats at jaw_gap for a parallel gripper, V-grooves to self-centre
        g = P["jaw_gap"]
        knob = box(g, g + 6, 40).translate([60 - g / 2, -(g + 6) / 2, 7])
        vee = [Manifold.cube([4, 4, 44], True).rotate([0, 0, 45]).translate([60 + sx * g / 2, 0, 27]) for sx in (-1, 1)]
        knob = knob - union(vee)
    else:
        knob = cyl(40, knob_r).translate([60, 0, 7])
    set_screw = cyl(14, P["m3_pilot"] / 2, seg=16).rotate([0, 90, 0]).translate([-12, 0, 7])
    return union([hub, arm, knob]) - set_screw


def bin_(length=None, width=96.0, height=40.0, wall=2.0):
    L = length or P["zone_len"]
    outer = box(L, width, height)
    inner = box(L - 2 * wall, width - 2 * wall, height).translate([wall, wall, wall])
    tag = box(P["tag"] + 0.4, 0.8, P["tag"] + 0.4).translate([(L - P["tag"]) / 2, -0.01, (height - P["tag"]) / 2 + 2])
    holes = [cyl(8, P["m3_pilot"] / 2, seg=16).rotate([90, 0, 0]).translate([L / 2 + dx, width + 1, height - 8]) for dx in (-10, 10)]
    return outer - union([inner, tag] + holes)


# ------------------------------------------------------------------ vortexer + centrifuge
def mini_ring(hole_d=None):
    od, h = P["mini_od"], P["mini_h"]
    ro, ri = od / 2, od / 2 - 2.0
    wall = tube(h, ro, ri, seg=72)
    floor = cyl(1.6, ro, seg=72)
    if hole_d:
        pitch = hole_d + 1.2
        pts = [(x, y) for x in np.arange(-ri, ri, pitch) for y in np.arange(-ri, ri, pitch * math.sqrt(3) / 2)]
        pts = [(x + (pitch / 2 if round(y / (pitch * math.sqrt(3) / 2)) % 2 else 0), y) for x, y in pts]
        holes = [cyl(4, hole_d / 2, seg=12).translate([x, y, -1]) for x, y in pts if math.hypot(x, y) < ri - hole_d / 2 - 0.6]
        floor = floor - union(holes)
    spigot = tube(3, ri - P["fit"], ri - 2.0, seg=72).translate([0, 0, -3])
    return union([wall, floor, spigot])


def mini_lid():
    ro = P["mini_od"] / 2
    lid = cyl(2, ro, seg=72) + tube(3, ro - 2 - P["fit"], ro - 4, seg=72).translate([0, 0, -3])
    hooks = [box(6, 4, 8).translate([sx * (ro - 1) - 3, -2, 2]) for sx in (-1, 1)]
    return union([lid] + hooks)


def vortex_puck():
    d = P["vortex_platform_d"]
    puck = cyl(10, d / 2, seg=96)
    socket = cyl(6, P["mini_od"] / 2 + P["fit"], seg=72).translate([0, 0, 5])
    hooks = [box(6, 4, 8).translate([sx * (d / 2 - 6) - 3, -2, 10]) for sx in (-1, 1)]
    return union([puck] + hooks) - socket


def tube_strainer(hole_d):
    ri = P["tube_id"] / 2 - 0.4
    cup = tube(25, ri, ri - 1.4)
    flange = tube(2, ri + 4, ri - 1.4).translate([0, 0, 25])
    floor = cyl(1.4, ri)
    pitch = hole_d + 1.0
    holes = [cyl(4, hole_d / 2, seg=12).translate([x, y, -1]) for x in np.arange(-ri, ri, pitch) for y in np.arange(-ri, ri, pitch)
             if math.hypot(x, y) < ri - 1.4 - hole_d / 2 - 0.4]
    tab = box(10, 6, 2).translate([ri + 2, -3, 25])
    return union([cup, flange, floor - union(holes), tab])


def grip_handle():
    g = P["jaw_gap"]
    base = box(40, 16, 4).translate([-20, -8, 0])
    body = box(g, 16, 22).translate([-g / 2, -8, 4])
    vee = [Manifold.cube([3, 3, 30], True).rotate([0, 0, 45]).translate([sx * g / 2, 0, 15]) for sx in (-1, 1)]
    tag = box(14.4, 14.4, 0.8).translate([-7.2, -7.2, 25.21])
    screws = [cyl(10, P["m3"] / 2, seg=16).translate([dx, 0, -1]) for dx in (-10, 10)]
    return union([base, body]) - union(vee + [tag] + screws)


# ------------------------------------------------------------------ export
def parts():
    out = {f"trommel_zone_{d:g}mm": drum_zone(d) for d in P["zone_holes"]}
    out.update({"trommel_cap_inlet": drum_cap("inlet"), "trommel_cap_outlet": drum_cap("outlet"),
                "trommel_stand_inlet": stand(math.tan(math.radians(P["incline_deg"])) * (3 * P["zone_len"] + 20)),
                "trommel_stand_outlet": stand(0.0), "trommel_crank_hand": crank(False), "trommel_crank_arm": crank(True),
                "trommel_bin": bin_(), "trommel_bin_oversize": bin_(length=60.0)})
    out.update({f"vortex_mini_sieve_{d:g}mm": mini_ring(d) for d in P["mini_holes"]})
    out.update({"vortex_mini_pan": mini_ring(None), "vortex_mini_lid": mini_lid(), "vortex_puck_76": vortex_puck()})
    out.update({f"centrifuge_tube_strainer_{d:g}mm": tube_strainer(d) for d in P["tube_holes"]})
    out["arm_grip_handle"] = grip_handle()
    return out


def to_trimesh(m):
    import trimesh
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=False)


def export(out_dir="print/parts"):
    import hashlib
    out = Path(out_dir); (out / "stl").mkdir(parents=True, exist_ok=True)
    rows = []
    for name, m in parts().items():
        t = to_trimesh(m)
        f = out / "stl" / f"{name}.stl"
        t.export(f)
        bb = t.bounds
        rows.append({"part": name, "stl": f"stl/{name}.stl", "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                     "watertight": bool(t.is_watertight), "volume_cm3": round(t.volume / 1000, 2), "triangles": len(t.faces),
                     "bbox_mm": [round(float(x), 1) for x in (bb[1] - bb[0])]})
        print(name, rows[-1]["bbox_mm"], rows[-1]["volume_cm3"], "cm3", "watertight" if t.is_watertight else "NOT WATERTIGHT", flush=True)
    (out / "parts.json").write_text(json.dumps({"params": P, "parts": rows}, indent=1))
    return rows


if __name__ == "__main__":
    export()


def assembly():
    """Trommel assembled on its axis (x), stands, crank and bins placed underneath; for review only."""
    import trimesh
    p = parts(); L = P["zone_len"]; s = P["spigot_len"]
    items = []
    def place(m, z, name, color):
        t = to_trimesh(m); t.apply_translation([0, 0, z]); t.visual.face_colors = color; items.append((name, t))
    place(p["trommel_cap_inlet"].mirror([0, 0, 1]), 3, "cap_inlet", [200, 200, 200, 255])
    for i, d in enumerate(P["zone_holes"]):
        place(p[f"trommel_zone_{d:g}mm"], i * L, f"zone_{d:g}", [[120, 170, 220, 255], [110, 200, 150, 255], [230, 170, 90, 255]][i])
    place(p["trommel_cap_outlet"].mirror([0, 0, 1]), 3 * L + s + 6, "cap_outlet", [200, 200, 200, 255])
    scene = trimesh.Scene()
    tilt = trimesh.transformations.rotation_matrix(math.radians(90 - 0), [0, 1, 0])
    for name, t in items:
        t.apply_transform(tilt); t.apply_translation([0, 0, P["axis_h"] + 5]); scene.add_geometry(t, node_name=name)
    for name, x, extra in (("stand_inlet", -18, True), ("stand_outlet", 3 * L + 30, False)):
        t = to_trimesh(p["trommel_stand_inlet" if extra else "trommel_stand_outlet"])
        t.apply_transform(trimesh.transformations.rotation_matrix(math.radians(90), [0, 0, 1])); t.apply_translation([x, 0, 0])
        t.visual.face_colors = [150, 120, 90, 255]; scene.add_geometry(t, node_name=name)
    for i in range(3):
        t = to_trimesh(p["trommel_bin"]); t.apply_translation([i * L, -48, 0]); t.visual.face_colors = [235, 235, 225, 255]
        scene.add_geometry(t, node_name=f"bin_{i}")
    t = to_trimesh(p["trommel_crank_hand"]); t.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-90), [0, 1, 0]))
    t.apply_translation([-40, 0, P["axis_h"] + 5]); t.visual.face_colors = [90, 90, 90, 255]; scene.add_geometry(t, node_name="crank")
    return scene


def render_previews(out_dir="print/parts", names=None, cols=5):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    out = Path(out_dir); rows = json.loads((out / "parts.json").read_text())["parts"]
    rows = [r for r in rows if not names or r["part"] in names]
    import trimesh
    n = len(rows); R = math.ceil(n / cols)
    fig = plt.figure(figsize=(cols * 3.2, R * 3.2), dpi=110)
    light = np.array([0.4, -0.5, 0.75]); light /= np.linalg.norm(light)
    for i, r in enumerate(rows):
        t = trimesh.load(out / r["stl"])
        ax = fig.add_subplot(R, cols, i + 1, projection="3d")
        shade = 0.35 + 0.65 * np.clip(t.face_normals @ light, 0, 1)
        col = np.c_[np.outer(shade, [0.55, 0.68, 0.82]), np.ones(len(shade))]
        pc = Poly3DCollection(t.vertices[t.faces], facecolors=col, edgecolor="none", linewidths=0)
        ax.add_collection3d(pc)
        c = t.bounds.mean(0); s = (t.bounds[1] - t.bounds[0]).max() / 2
        ax.set_xlim(c[0] - s, c[0] + s); ax.set_ylim(c[1] - s, c[1] + s); ax.set_zlim(c[2] - s, c[2] + s)
        ax.view_init(elev=28, azim=-55); ax.set_axis_off()
        ax.set_title(f"{r['part']}\n{r['bbox_mm'][0]:g} x {r['bbox_mm'][1]:g} x {r['bbox_mm'][2]:g} mm", fontsize=7.5)
    fig.tight_layout(); f = out / "previews.png"; fig.savefig(f); plt.close(fig)
    return f


def render_assembly(out_dir="print/parts", views=((22, -60), (8, -90), (60, -20))):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    sc = assembly(); light = np.array([0.4, -0.6, 0.7]); light /= np.linalg.norm(light)
    meshes = [g.copy().apply_transform(sc.graph[n][0]) for n in sc.graph.nodes_geometry for g in [sc.geometry[sc.graph[n][1]]]]
    fig = plt.figure(figsize=(15, 5.2), dpi=120)
    allv = np.vstack([m.vertices for m in meshes]); c = (allv.min(0) + allv.max(0)) / 2; s = (allv.max(0) - allv.min(0)).max() / 2
    for k, (el, az) in enumerate(views):
        ax = fig.add_subplot(1, len(views), k + 1, projection="3d")
        for m in meshes:
            fc = np.asarray(m.visual.face_colors[:, :3], float) / 255
            sh = (0.35 + 0.65 * np.clip(m.face_normals @ light, 0, 1))[:, None]
            ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolors=np.c_[fc * sh, np.ones(len(sh))], edgecolor="none"))
        ax.set_xlim(c[0] - s, c[0] + s); ax.set_ylim(c[1] - s, c[1] + s); ax.set_zlim(c[2] - s, c[2] + s)
        ax.view_init(elev=el, azim=az); ax.set_axis_off()
    fig.suptitle("Trommel assembly (hand crank): 2 mm -> 4 mm -> 7 mm zones, bins below, oversize exits the open end", fontsize=10)
    fig.tight_layout(); f = Path(out_dir) / "trommel_assembly.png"; fig.savefig(f); plt.close(fig)
    return f
