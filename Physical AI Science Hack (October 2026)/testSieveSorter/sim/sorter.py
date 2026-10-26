"""Sorter sim core: drop a mix of grains and insects into a design, shake it, and record where
everything goes. Units mm, g, s.

The sim runs in the tray frame: design geoms are static and the shake is a uniform pseudo-force,
gravity minus the tray's acceleration, which is exact for a tray that only translates. The lab
frame is the tray frame shifted by the tray displacement; spray jets stay fixed in the lab.

Stroke direction: along the design's flow axis by default; "angle_deg" tilts it up toward +z (0 = flow axis,
90 = straight up, in between = an angled throw like a lab sieve shaker); "axis" (a 3-vector, Python API) overrides.
Peak acceleration of a sine stroke is amp_mm * (2 pi freq_hz)^2; above g (9810 mm/s^2) a vertical stroke throws.

Stroke profiles:
    sine            amp_mm, freq_hz
    constant_speed  amp_mm, freq_hz or speed_mm_s, ramp_s: constant speed with smoothed reversals.
                    BioKEA's firmware (github.com/BioKEA/BugSorter src/main.cpp) runs a 2 cm stroke
                    (amp_mm=10) at 5 mm/s by default, capped at 50 mm/s, with no acceleration ramp
    sawtooth        amp_mm, freq_hz, forward_fraction, ramp_s: slow stroke along the axis, fast return
    csv             csv: a measured "t_s,x_mm" file (looped), smoothed before differentiating
    none
    seesaw          deg, period_s, shape, ...: each level of an inserts: tower rocks on its own hinge about Y,
                    neighbours in opposite phase (rocking.py); vib_mm, vib_hz: a small fast buzz of the whole
                    tower on top, as a translation stroke (none by default)

Run from sim\\:
    <venv python> sorter.py --design pool:w5p0,t1p4 --mix rice=30,quinoa=30,chickpea=8,pasta=8 \\
        --stroke sine:amp_mm=3,freq_hz=10 --duration 10 --out out/runs/demo
    <venv python> sorter.py --design inserts:5mm --mix pasta=15,rice=40         --stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90 --duration 10     (demo tray, shaken up and down)
    <venv python> viewer.py out/runs/demo --open
"""
import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import mujoco
import numpy as np

import clumps
import designs
import rocking

G = 9810.0
SOLIMP = "0.95 0.99 0.0001"
MEMORY = "128M"           # MuJoCo arena per run; sweeps run about 10 at once
CSV_SMOOTH_S = 0.005
# While particles settle, their speed is damped at this rate (1/s), capping the fall at about
# g / rate = 100 mm/s. Soft contacts let a hard landing push a grain through an opening slightly
# smaller than it, which a rigid printed part would never allow.
SETTLE_DAMPING = 100.0
GEOM_TYPES = {mujoco.mjtGeom.mjGEOM_SPHERE: "sphere", mujoco.mjtGeom.mjGEOM_CAPSULE: "capsule",
              mujoco.mjtGeom.mjGEOM_ELLIPSOID: "ellipsoid", mujoco.mjtGeom.mjGEOM_CYLINDER: "cylinder",
              mujoco.mjtGeom.mjGEOM_BOX: "box"}
GEOM_NSIZE = {"sphere": 1, "capsule": 2, "ellipsoid": 3, "cylinder": 2, "box": 3}


@dataclass
class RunConfig:
    design: str = "pool:w5p0,t1p4"
    mix: dict = field(default_factory=lambda: {"rice": 30, "quinoa": 30, "chickpea": 8, "pasta": 8})
    stroke: dict = field(default_factory=lambda: {"profile": "sine", "amp_mm": 3.0, "freq_hz": 10.0})
    duration_s: float = 10.0
    settle_s: float = 1.0
    seed: int = 0
    dt: float = 5e-4
    contact: dict = field(default_factory=lambda: {"friction": 0.4, "timeconst": 0.002, "dampratio": 1.0})
    spray: dict | None = None
    clump: dict | None = None        # clumps.py: a clump of specimens and debris joined by breakable bonds
    record_fps: float = 30.0
    out_dir: str | None = None


def make_particle(kind, rng):
    if kind.startswith("insect_"):
        import insects
        return insects.make(kind, rng)
    if kind in clumps.DEBRIS:
        return clumps.make_debris(kind, rng)
    import grains
    return grains.make(kind, rng)


def smooth(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same") if n > 1 else x


def stroke_axis(stroke, design):
    """Unit stroke direction in the tray frame. stroke["axis"] (a 3-vector) wins; else stroke["angle_deg"] tilts the
    design's flow axis up toward +z (0 = along the flow axis, 90 = straight up); else the flow axis."""
    if stroke.get("axis") is not None and stroke.get("angle_deg") is not None:
        raise ValueError("give the stroke an axis or an angle_deg, not both")
    if stroke.get("axis") is not None:
        axis = np.array(stroke["axis"], dtype=float)
    else:
        flow = np.array(design.stroke_axis, dtype=float)
        flow[2] = 0.0
        th = np.radians(stroke.get("angle_deg", 0.0))
        axis = np.cos(th) * flow / np.linalg.norm(flow) + np.sin(th) * np.array([0.0, 0.0, 1.0])
    return axis / np.linalg.norm(axis)


def stroke_profile(stroke, n, dt):
    """Displacement, velocity and acceleration along the stroke axis at each of n steps."""
    p = stroke.get("profile", "sine")
    t = np.arange(n) * dt
    if p == "none":
        return np.zeros(n), np.zeros(n), np.zeros(n)
    amp, f = stroke.get("amp_mm", 3.0), stroke.get("freq_hz", 10.0)
    if "speed_mm_s" in stroke:                       # constant_speed by firmware settings: speed and stroke length
        f = stroke["speed_mm_s"] / (4 * amp)
    if p == "sine":
        w = 2 * np.pi * f
        return amp * np.sin(w * t), amp * w * np.cos(w * t), -amp * w * w * np.sin(w * t)
    ramp = max(1, round(stroke.get("ramp_s", 0.01) / dt))
    if p in ("constant_speed", "sawtooth"):
        phase = (t * f) % 1.0
        r = 0.5 if p == "constant_speed" else stroke.get("forward_fraction", 0.7)
        v = np.where(phase < r, 1.0 / r, -1.0 / (1.0 - r))   # zero net travel per cycle
        v = smooth(v, ramp)
    elif p == "csv":
        rows = np.loadtxt(stroke["csv"], delimiter=",", skiprows=1)
        tt, xx = rows[:, 0] - rows[0, 0], rows[:, 1] - rows[:, 1].mean()
        x = np.interp(t % tt[-1], tt, xx)
        x = smooth(x, max(1, round(CSV_SMOOTH_S / dt)))
        v = np.gradient(x, dt)
        return x, v, np.gradient(smooth(v, max(1, round(CSV_SMOOTH_S / dt))), dt)
    else:
        raise ValueError(f"unknown stroke profile {p!r}")
    x = np.cumsum(v) * dt
    x -= (x.max() + x.min()) / 2
    k = amp / max(x.max(), 1e-9)                     # scale so the peak displacement is amp
    x, v = x * k, v * k
    return x, v, np.gradient(v, dt)


def place(particles, spawn, rng):
    """Positions packed from the bottom of the spawn box, no bounding spheres overlapping."""
    x0, x1, y0, y1, z0, z1 = spawn
    centres, radii, out = np.zeros((0, 3)), np.zeros(0), [None] * len(particles)
    order = sorted(range(len(particles)), key=lambda i: -particles[i].dims["span"])
    for i in order:
        dims = particles[i].dims
        r = min(dims["span"] / 2, dims["length"]) * 1.05      # long thin legs may interleave
        rx, ry, rz = (min(r, (b - a) / 2 - 0.01) for a, b in ((x0, x1), (y0, y1), (z0, z1)))
        for z in np.arange(z0 + rz, z1 - rz + 1e-9, 1.0):
            p = np.column_stack([rng.uniform(x0 + rx, x1 - rx, 40), rng.uniform(y0 + ry, y1 - ry, 40), np.full(40, z)])
            ok = np.all(np.linalg.norm(p[:, None] - centres[None], axis=2) > r + radii, axis=1)
            if ok.any():
                out[i] = p[np.argmax(ok)]
                centres, radii = np.vstack([centres, out[i]]), np.append(radii, r)
                break
        else:
            raise RuntimeError(f"no room to drop particle {i} ({particles[i].kind}); use fewer particles")
    return out


def tray_xml(design):
    assets, geoms = [], []
    for i, g in enumerate(design.geoms):
        rgba = " ".join(f"{c:g}" for c in g["rgba"])
        if g["type"] == "mesh":
            vert = " ".join(f"{c:.4f}" for v in g["vertices"] for c in v)
            assets.append(f'<mesh name="tray{i}" vertex="{vert}"/>')
            geoms.append(f'<geom name="tray{i}" type="mesh" mesh="tray{i}" rgba="{rgba}"/>')
        else:
            geoms.append(f'<geom name="tray{i}" type="{g["type"]}" size="{" ".join(f"{c:.4f}" for c in g["size"])}" '
                         f'pos="{" ".join(f"{c:.4f}" for c in g["pos"])}" quat="{" ".join(f"{c:.6f}" for c in g["quat"])}" '
                         f'rgba="{rgba}"/>')
    return "".join(assets), "".join(geoms)


def build_model(cfg, design, particles, rng, extras="", rock=None, clump=None):
    c = cfg.contact
    mu = c["friction"]
    pos = place(particles, design.spawn, rng) if clump is None else clump.place(particles, design.spawn, rng)
    bodies = []
    for i, (p, xyz) in enumerate(zip(particles, pos)):
        q = rng.normal(size=4)
        q /= np.linalg.norm(q)
        if clump is not None:     # the clump's particles keep their packed orientations
            q = clump.quat(i, q)
        name = f"p{i:03d}"
        bodies.append(f'<body name="{name}" pos="{xyz[0]:.4f} {xyz[1]:.4f} {xyz[2]:.4f}" '
                      f'quat="{q[0]:.5f} {q[1]:.5f} {q[2]:.5f} {q[3]:.5f}" childclass="particle">'
                      f'<freejoint/>{p.xml.replace("{p}", name)}</body>')
    assets, tray = tray_xml(design)
    levels = ""
    if rock is not None:          # seesaw: the tray geoms move onto one hinged body per level, before the particles
        tray, levels = rock.split_xml(assets, tray)
        extras += rock.contact_xml()
    if clump is not None:         # the clump's breakable bonds
        extras += clump.equality_xml()
    xml = f"""<mujoco model="{design.name}">
  <option timestep="{cfg.dt}" gravity="0 0 {-G}" integrator="implicitfast"/>
  <size memory="{MEMORY}"/>
  <visual><global offwidth="1280" offheight="720"/><quality shadowsize="4096"/></visual>
  <default>
    <geom solref="{c['timeconst']} {c['dampratio']}" solimp="{SOLIMP}" friction="{mu} 0.005 0.0001"/>
    <default class="particle"><geom priority="1"/></default>
  </default>
  <asset>{assets}</asset>
  <worldbody>
    <light pos="0 -80 300" dir="0 0.25 -1" diffuse="0.8 0.8 0.8"/>
    <camera name="iso" pos="0 -170 170" xyaxes="1 0 0 0 0.707 0.707"/>
    {tray}
    {levels}{"".join(bodies)}
  </worldbody>
  {extras}
</mujoco>"""
    return mujoco.MjModel.from_xml_string(xml)


def assign_zones(xyz, design, bounds, local=None):
    """Zone index per particle root: design zones in order, then between, then lost. local(k, xyz), if given,
    returns xyz in zone k's own frame (a seesaw level's)."""
    n_z = len(design.zones)
    zone = np.full(len(xyz), n_z, dtype=np.int32)                  # between
    for k in reversed(range(n_z)):
        x0, x1, y0, y1, z0, z1 = design.zones[k]["box"]
        p = xyz if local is None else local(k, xyz)
        inside = ((p[:, 0] >= x0) & (p[:, 0] <= x1) & (p[:, 1] >= y0) & (p[:, 1] <= y1)
                  & (p[:, 2] >= z0) & (p[:, 2] <= z1))
        zone[inside] = k
    lo, hi = bounds
    lost = np.any(xyz < lo, axis=1) | np.any(xyz > hi, axis=1)
    zone[lost] = n_z + 1
    return zone


def scene_geoms(design, m):
    """Tray geoms for the viewer; a mesh comes out as the convex hull MuJoCo compiled, in the tray frame."""
    out = []
    for i, g in enumerate(design.geoms):
        if g["role"] == "lid":
            continue
        if g["type"] == "mesh":
            gid = m.geom(f"tray{i}").id
            k = m.geom_dataid[gid]
            v0, nv, f0, nf = m.mesh_vertadr[k], m.mesh_vertnum[k], m.mesh_faceadr[k], m.mesh_facenum[k]
            rot = np.zeros(9)
            mujoco.mju_quat2Mat(rot, m.geom_quat[gid])
            verts = m.mesh_vert[v0:v0 + nv] @ rot.reshape(3, 3).T + m.geom_pos[gid]
            out.append({"type": "mesh", "vertices": verts.round(4).tolist(), "faces": m.mesh_face[f0:f0 + nf].tolist(),
                        "rgba": g["rgba"], "role": g["role"]})
        else:
            out.append({k: g[k] for k in ("type", "size", "pos", "quat", "rgba", "role")})
    return out


def body_geoms(m, b):
    out = []
    for g in np.flatnonzero(m.geom_bodyid == b):
        t = GEOM_TYPES[int(m.geom_type[g])]
        out.append({"type": t, "size": m.geom_size[g][:GEOM_NSIZE[t]].round(5).tolist(),
                    "pos": m.geom_pos[g].round(5).tolist(), "quat": m.geom_quat[g].round(6).tolist(),
                    "rgba": m.geom_rgba[g].round(3).tolist()})
    return out


def run(cfg: RunConfig) -> dict:
    rng = np.random.default_rng(cfg.seed)
    design = designs.build(cfg.design)
    rock = rocking.Seesaw.of(cfg, design)            # None unless the stroke is a seesaw
    kinds = list(cfg.mix)
    particles = [make_particle(k, rng) for k in kinds for _ in range(cfg.mix[k])]
    cl = clumps.Clumps.of(cfg, rng)                  # None unless cfg.clump; its particles go after the loose ones
    if cl:
        particles += cl.particles
        kinds += [k for k in cl.kinds if k not in kinds]
    names = [f"p{i:03d}" for i in range(len(particles))]

    sp = None
    extras = ""
    if cfg.spray:
        import spray
        jets = cfg.spray.get("jets", "default")
        if jets == "default":
            jets = design.jets_default
        elif jets == "bench":                       # the nozzles the team measured (BENCH.md step 7)
            jets = spray.jets_from_csv(Path(__file__).resolve().parent / "bench" / "jets.csv")
        jets = [spray.Jet(**j) for j in jets]
        extras = spray.Spray.mjcf_extras(names, cfg.spray.get("params"))
    m = build_model(cfg, design, particles, rng, extras, rock, cl)
    d = mujoco.MjData(m)
    roots = np.array([m.body(n).id for n in names])
    # every particle body, roots and children. The seesaw's level bodies come first, so their hinge DOFs are
    # eliminated last: every contact touches a hinge, and after the particles they made the solver's
    # factorization dense (about 30x the wall time per step)
    pbodies = np.arange(1 + (rock.n if rock else 0), m.nbody)
    tray_body = np.isin(np.arange(m.nbody), [0, *(rock.bind(m).body if rock else [])])
    if cfg.spray:
        sp = spray.Spray(m, d, jets, list(pbodies), cfg.spray.get("params"))

    axis = rock.vib_axis() if rock else stroke_axis(cfg.stroke, design)
    n_settle, n_shake = round(cfg.settle_s / cfg.dt), round(cfg.duration_s / cfg.dt)
    x, v, a = rock.vibration(n_shake, cfg.dt) if rock else stroke_profile(cfg.stroke, n_shake, cfg.dt)
    x, v, a = (np.concatenate([np.zeros(n_settle), s]) for s in (x, v, a))
    steps = n_settle + n_shake

    extent = np.array([[g["pos"][i] + s * g["size"][i] for g in design.geoms if g["type"] == "box" for s in (-1, 1)]
                       for i in range(3)])
    bounds = (extent.min(axis=1) - 5.0, extent.max(axis=1) + 5.0)
    if rock:
        bounds = rock.widen(bounds)
    zone_names = [z["name"] for z in design.zones] + ["between", "lost"]
    kind_idx = np.array([kinds.index(p.kind) for p in particles])

    fps = cfg.record_fps if cfg.out_dir and cfg.record_fps > 0 else 10.0
    every = max(1, round(1.0 / (fps * cfg.dt)))
    rec = {"t": [], "tray_d": [], "pos": [], "quat": [], "zone_counts": [], "wet": [], "level_q": []}
    recording = bool(cfg.out_dir and cfg.record_fps > 0)
    max_pen = max_pen_pp = 0.0
    t0 = time.perf_counter()
    settle_keep = np.exp(-SETTLE_DAMPING * cfg.dt)
    # MuJoCo answers a NaN/Inf/huge QPOS, QVEL or QACC by resetting mjData and carrying on, so an unstable
    # run would still finish with plausible-looking results. Record each reset (step time) instead of hiding it.
    # The reset also clears the warning counters, so it is detected by d.time going backwards.
    resets = []
    if cl:
        cl.bind(m, d, design, rock, sp, every, n_settle)
    for i in range(steps):
        m.opt.gravity[:] = -a[i] * axis
        m.opt.gravity[2] -= G
        if i < n_settle:
            d.qvel *= settle_keep
        if sp is not None:
            d.xfrc_applied[:] = 0.0
            sp.step(m, d, d.time, x[i] * axis, v[i] * axis)
        if rock:
            rock.drive(d, i)
        t_before = d.time
        mujoco.mj_step(m, d)
        if d.time < t_before:
            resets.append(round((i + 1) * cfg.dt, 5))
        if cl:
            cl.step(m, d, i)                         # break overloaded bonds, log peak contact forces
        if i >= n_settle and i % 10 == 0 and d.ncon:   # overlap where it matters: particle against tray
            dist = d.contact.dist[:d.ncon]
            on_tray = np.any(tray_body[m.geom_bodyid[d.contact.geom[:d.ncon]]], axis=1)
            if on_tray.any():
                max_pen = max(max_pen, -float(dist[on_tray].min()))
            if (~on_tray).any():
                max_pen_pp = max(max_pen_pp, -float(dist[~on_tray].min()))
        if i % every == 0 or i == steps - 1:
            zone = assign_zones(d.xpos[roots], design, bounds, rock.zone_frames(d) if rock else None)
            counts = np.zeros((len(kinds), len(zone_names)), dtype=np.int32)
            np.add.at(counts, (kind_idx, zone), 1)
            rec["t"].append(d.time)
            rec["tray_d"].append(x[i] * axis)
            rec["zone_counts"].append(counts)
            if recording:
                rec["pos"].append(d.xpos[pbodies].astype(np.float32))
                rec["quat"].append(d.xquat[pbodies].astype(np.float32))
                if sp is not None:
                    rec["wet"].append(np.asarray(sp.wet)[pbodies].astype(np.float32))
                if rock:
                    rec["level_q"].append(rock.quats(d))
    wall = time.perf_counter() - t0

    final = assign_zones(d.xpos[roots], design, bounds, rock.zone_frames(d) if rock else None)
    plist = [{"name": n, "kind": p.kind, "group": p.group, "dims": {k: round(float(val), 3) for k, val in p.dims.items()},
              "final_zone": zone_names[z], "ideal_zone": design.ideal_zone(p.dims)}
             for n, p, z in zip(names, particles, final)]
    zc = np.array(rec["zone_counts"])
    results = {
        "config": asdict(cfg), "design": design.name, "design_info": design.info,
        "zones": zone_names, "kinds": kinds,
        "counts": {k: {zn: int(zc[-1, ki, zi]) for zi, zn in enumerate(zone_names)} for ki, k in enumerate(kinds)},
        "recovery": {k: round(float(np.mean([p["final_zone"] == p["ideal_zone"] for p in plist if p["kind"] == k])), 4)
                     for k in kinds if any(p.kind == k for p in particles)},
        "particles": plist,
        "timeseries": {"t": [round(t, 4) for t in rec["t"]],
                       "counts": {k: {zn: zc[:, ki, zi].tolist() for zi, zn in enumerate(zone_names)}
                                  for ki, k in enumerate(kinds)}},
        "max_penetration_mm": round(max_pen, 5), "max_penetration_particles_mm": round(max_pen_pp, 5), "sim_s": round(d.time, 3), "wall_s": round(wall, 2), "steps": steps,
        "unstable_resets": resets,
    }
    if rock:
        results["seesaw"] = rock.summary()
    if cl:
        results["clumps"] = cl.metrics(plist, d)
    if cfg.out_dir:
        write_recording(Path(cfg.out_dir), cfg, design, m, results, rec, kinds, zone_names, particles, names, sp, rock)
    return results


def write_recording(out, cfg, design, m, results, rec, kinds, zone_names, particles, names, sp, rock=None):
    out.mkdir(parents=True, exist_ok=True)
    by_name = dict(zip(names, particles))
    bodies = []
    for b in range(1 + (rock.n if rock else 0), m.nbody):
        root = m.body(int(m.body_rootid[b])).name
        p = by_name[root]
        bodies.append({"name": m.body(b).name, "particle": root, "kind": p.kind, "group": p.group,
                       "geoms": body_geoms(m, b)})
    jets = []
    if sp is not None:
        jets = [{"pos_lab": list(map(float, j.pos_lab)), "dir": list(map(float, j.dir)),
                 "half_angle_deg": j.half_angle_deg, "range_mm": j.range_mm} for j in sp.jets]
    scene = {"units": "mm", "fps": cfg.record_fps, "dt": cfg.dt, "n_frames": len(rec["t"]),
             "config": asdict(cfg), "design": design.name,
             "tray": {"geoms": scene_geoms(design, m)}, "bodies": bodies, "kinds": kinds,
             "zones": [*design.zones, {"name": "between"}, {"name": "lost"}], "jets": jets,
             "results": {k: v for k, v in results.items() if k != "timeseries"}}
    if rock:                                         # per level: pivot, axis, geoms (rocking.py)
        scene["levels"] = rock.scene_levels(m)
    (out / "scene.json").write_text(json.dumps(scene, default=float))
    arrays = {"t": np.array(rec["t"]), "tray_d": np.array(rec["tray_d"], dtype=np.float32),
              "zone_counts": np.array(rec["zone_counts"], dtype=np.int32)}
    if rec["pos"]:
        arrays["pos"], arrays["quat"] = np.array(rec["pos"]), np.array(rec["quat"])
    if rec["wet"]:
        arrays["wet"] = np.array(rec["wet"])
    if rec["level_q"]:                               # frames x levels x 4 (w x y z), each level in the lab
        arrays["level_q"] = np.array(rec["level_q"], dtype=np.float32)
    np.savez_compressed(out / "traj.npz", **arrays)
    (out / "results.json").write_text(json.dumps(results, indent=1, default=float))


def parse_kv(s):
    """'rice=30,quinoa=30' -> {'rice': 30, 'quinoa': 30}; numbers become int or float."""
    out = {}
    for part in filter(None, s.split(",")):
        k, _, val = part.partition("=")
        try:
            out[k] = int(val)
        except ValueError:
            try:
                out[k] = float(val)
            except ValueError:
                out[k] = val
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--design", default=RunConfig.design)
    ap.add_argument("--mix", default="rice=30,quinoa=30,chickpea=8,pasta=8")
    ap.add_argument("--stroke", default="sine:amp_mm=3,freq_hz=10", help="profile:key=val,...")
    ap.add_argument("--duration", type=float, default=10.0)
    ap.add_argument("--settle", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dt", type=float, default=5e-4)
    ap.add_argument("--friction", type=float, default=0.4)
    ap.add_argument("--timeconst", type=float, default=0.002, help="contact stiffness time constant, s (>= 2 dt)")
    ap.add_argument("--spray", choices=["none", "default", "bench"], default="none",
                    help="default: the design's placeholder jets; bench: bench/jets.csv")
    ap.add_argument("--clump", default=None, help="clumps.py: kinds and options, e.g. rice=50,quinoa=50,pasta=6,"
                    "leaf=1,twig=2,dirt=10,bond=medium (weak|medium|strong)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--out", default=None, help="run dir for scene.json, traj.npz, results.json")
    args = ap.parse_args()
    profile, _, rest = args.stroke.partition(":")
    cfg = RunConfig(design=args.design, mix=parse_kv(args.mix), stroke={"profile": profile, **parse_kv(rest)},
                    duration_s=args.duration, settle_s=args.settle, seed=args.seed, dt=args.dt,
                    contact={"friction": args.friction, "timeconst": args.timeconst, "dampratio": 1.0},
                    spray=None if args.spray == "none" else {"jets": args.spray},
                    clump=clumps.parse(args.clump) if args.clump else None,
                    record_fps=args.fps, out_dir=args.out)
    r = run(cfg)
    print(f"{r['design']}: {r['sim_s']} s simulated in {r['wall_s']} s wall, {r['steps']} steps, "
          f"max overlap {r['max_penetration_mm']} mm on the tray, {r['max_penetration_particles_mm']} mm between particles")
    if "seesaw" in r:
        c = r["seesaw"]["clearance"]
        print(f"  seesaw +/-{r['seesaw']['deg']:g} deg, {r['seesaw']['period_s']:g} s: neighbouring boxes come within "
              f"{c['min_mm']} mm" + ("  TOUCHING: raise pitch= (rocking.py)" if c["touching"] else ""))
    if "clumps" in r:
        print(clumps.summary(r["clumps"]))
    if r["unstable_resets"]:
        print(f"UNSTABLE: MuJoCo reset the state {len(r['unstable_resets'])} times (at {r['unstable_resets'][:5]} s); "
              "the results are not valid")
    for k, c in r["counts"].items():
        print(f"  {k:16s} recovery {r['recovery'].get(k, 0):.2f}  " + "  ".join(f"{z} {n}" for z, n in c.items() if n))
    if args.out:
        print("recorded to", args.out)


if __name__ == "__main__":
    main()
