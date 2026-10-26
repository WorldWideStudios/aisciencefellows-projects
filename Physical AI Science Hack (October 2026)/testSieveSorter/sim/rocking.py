"""Per-level seesaw for a stacked holder tower (docs/SYSTEM.md sections 3 and 5). Units mm, g, s.

Each holder box of an inserts: tower (the catch pan too) becomes its own body on a hinge. The hinge axis is
Y (the tray's width) through the box's centre: x = y = 0, half way up the box. The two short ends tip up and
down in turn, and neighbouring levels run in opposite phase. The run is in the lab frame (gravity -Z), and the
hinge angles are prescribed: before every step the hinge qpos and qvel are written from

    theta_k(t) = sign_k * deg * f(t / period_s),   sign_k = +1, -1, +1, ... from the top level down

so contacts see the trays' real velocities and nothing approximates the rotation. theta > 0 tips the +X end
(the mounting-tab end) down. A level body is very heavy, with its mass on the hinge axis, so particles can't
move it within a step either.

Stroke (sorter.py --stroke seesaw:k=v,...; every key optional):
    deg        amplitude, degrees either side of level (10: SYSTEM.md's default while the user picks from 5-15)
    period_s   one full cycle, s (2.0)
    shape      constant_speed: constant angular speed with reversals smoothed over ramp_s, as the firmware
               drives its stage (default); sine
    ramp_s     reversal time for constant_speed (0.02)
    ramp_in_s  ease the amplitude in from zero over this long after the settle (0: start at full speed)
    alternate  1: neighbours in opposite phase (default); 0: every level in phase
    catch      1: the catch pan rocks too, as the next level down (default); 0: it stays level
  A small fast vibration on top of the seesaw (the handheld tool's buzz, the puck's 40 Hz), off by default:
    vib_mm     amplitude of a sine buzz of the whole tower, mm (0: off)
    vib_hz     its frequency (40); peak acceleration is vib_mm * (2 pi vib_hz)^2, so 0.3 mm at 40 Hz is 1.9 g
    vib_angle_deg  its direction: 0 along X (the tilt direction), 90 straight up (90)
    vib_deg    a fast angular buzz added to every hinge, degrees, in each level's own phase (0: off)
  The buzz moves every level together, so sorter.py applies it the way it applies any translation stroke: as a
  uniform pseudo-force, exact for a shared translation, and recorded as tray_d. The hinges still turn in that
  translating frame.

The sim has the trays only: no frame, pins or motor (the tower in rig.py is display only). Tray-tray contacts
are switched off, since the trays are driven; instead clearance() checks how close neighbouring boxes come over
a cycle, and pitch_needed() finds the pitch that keeps them apart. Translation strokes keep sorter.py's
tray-frame path; a seesaw run has no translation.

Run from sim\\ to print the clearance and the pitch needed:
    <venv python> rocking.py inserts:5mm,2mm,pitch=110 --deg 20,25,30
"""
import argparse
import dataclasses
import re

import mujoco
import numpy as np

DEFAULTS = {"deg": 10.0, "period_s": 2.0, "shape": "constant_speed", "ramp_s": 0.02, "ramp_in_s": 0.0,
            "alternate": 1, "catch": 1, "vib_mm": 0.0, "vib_hz": 40.0, "vib_angle_deg": 90.0, "vib_deg": 0.0}
G = 9810.0                # mm/s^2
LEVEL_MASS = 1e6          # g: a driven tray; particles weigh a few hundredths of a gram
LEVEL_INERTIA = 1e10      # g mm^2, every axis, and the same again as hinge armature
CLEARANCE_SAMPLES = 41    # poses checked over one cycle (f from -1 to 1)


def profile(cfg, n_settle, n_shake, dt):
    """f(t) in [-1, 1] and df/dt (1/s) at every step: zero through the settle, then the seesaw, starting level
    and rising."""
    t = np.arange(n_shake) * dt
    T = cfg["period_s"]
    if cfg["shape"] == "sine":
        f, df = np.sin(2 * np.pi * t / T), (2 * np.pi / T) * np.cos(2 * np.pi * t / T)
    elif cfg["shape"] == "constant_speed":
        w = max(1, round(cfg["ramp_s"] / dt))
        tt = np.arange(-w, n_shake + w) * dt
        sq = np.where(((tt / T) % 1.0 + 0.25) % 1.0 < 0.5, 1.0, -1.0)    # rising through level at t = 0
        v = np.convolve(sq, np.ones(w) / w, mode="same")[w:w + n_shake] if w > 1 else sq[w:w + n_shake]
        f = np.concatenate([[0.0], np.cumsum(v[:-1])]) * dt * 4 / T
        k = 1.0 / max(np.abs(f).max(), 1e-9) if n_shake * dt >= T / 4 else 1.0
        f, df = f * k, v * (4 / T) * k
    else:
        raise ValueError(f"unknown seesaw shape {cfg['shape']!r}: use constant_speed or sine")
    if cfg["ramp_in_s"] > 0:                      # smoothstep envelope
        s = np.clip(t / cfg["ramp_in_s"], 0.0, 1.0)
        e, de = s * s * (3 - 2 * s), np.where(s < 1, 6 * s * (1 - s) / cfg["ramp_in_s"], 0.0)
        f, df = e * f, de * f + e * df
    z = np.zeros(n_settle)
    return np.concatenate([z, f]), np.concatenate([z, df])


def geom_centre_z(g):
    return float(np.mean([v[2] for v in g["vertices"]])) if g["type"] == "mesh" else float(g["pos"][2])


def rot_y(th):
    c, s = np.cos(th), np.sin(th)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def find_levels(design):
    """The tower's boxes, top to bottom with the catch pan last: zone, box bottom z, pivot, and the design geoms
    on each. A geom goes to the highest box whose bottom is at or below the geom's centre, so the invisible
    walls above the top box rock with it and the plate under the catch pan with the pan. A lid more than a box
    height under the catch pan (the tub floor of a spaced tower) stays in the lab."""
    info = design.info
    if "layers" not in info or "catch_z_mm" not in info or not all("holder_z_mm" in L for L in info["layers"]):
        raise ValueError(f"the seesaw needs a tower of holder boxes (inserts:...), not {design.name}")
    boxes = [(L["zone"], *L["holder_z_mm"]) for L in info["layers"]]
    H = boxes[0][2] - boxes[0][1]
    boxes.append((design.zones[-1]["name"], 0.0, H))
    if info.get("pitch_mm", H) <= H:
        raise ValueError(f"{design.name}: the boxes sit rim on rim, so they can't seesaw; space them with "
                         f"pitch=<mm> (rocking.py pitch_needed says how much)")
    levels = [{"name": f"level{k}", "zone": zone, "z0": z0, "pivot": [0.0, 0.0, (z0 + z1) / 2], "geoms": []}
              for k, (zone, z0, z1) in enumerate(boxes)]
    static = []
    for i, g in enumerate(design.geoms):
        zc = geom_centre_z(g)
        if g["role"] == "lid" and zc < -H:
            static.append(i)
            continue
        k = min((k for k, L in enumerate(levels) if L["z0"] <= zc), default=len(levels) - 1)
        levels[k]["geoms"].append(i)
    return levels, static


class Seesaw:
    """One tower's seesaw: builds the level bodies, drives their hinges, and reports per level."""

    @classmethod
    def of(cls, cfg, design):
        """A Seesaw for a RunConfig whose stroke profile is "seesaw", else None."""
        if cfg.stroke.get("profile") != "seesaw":
            return None
        return cls(cfg.stroke, design, cfg.dt, round(cfg.settle_s / cfg.dt), round(cfg.duration_s / cfg.dt))

    def __init__(self, stroke, design, dt, n_settle, n_shake):
        unknown = set(stroke) - set(DEFAULTS) - {"profile"}
        if unknown:
            raise ValueError(f"unknown seesaw option(s) {sorted(unknown)}: use {sorted(DEFAULTS)}")
        self.cfg = {**DEFAULTS, **{k: v for k, v in stroke.items() if k != "profile"}}
        self.design = design
        self.levels, self.static = find_levels(design)
        self.n = len(self.levels)
        amp = np.radians(self.cfg["deg"])
        for k, L in enumerate(self.levels):
            L["sign"] = (-1) ** k if self.cfg["alternate"] else 1
            catch = k == self.n - 1
            L["amp_rad"] = 0.0 if catch and not self.cfg["catch"] else amp * L["sign"]
        self.f, self.df = profile(self.cfg, n_settle, n_shake, dt)
        w, t = 2 * np.pi * self.cfg["vib_hz"], np.arange(n_shake) * dt
        z = np.zeros(n_settle)
        self.g, self.dg = np.concatenate([z, np.sin(w * t)]), np.concatenate([z, w * np.cos(w * t)])
        self.zone_level = {L["zone"]: k for k, L in enumerate(self.levels)}
        self.clear = None

    # ---------- model ----------
    def split_xml(self, assets, tray):
        """sorter.tray_xml's output -> (geoms that stay in the lab, one hinged <body> per level). Each body sits at
        the origin, so its geoms keep their tray-frame coordinates (and their names, tray<i>). Also checks the
        clearance between neighbouring levels."""
        geoms = tray_geoms(self.design, tray)
        self.clear = clearance(self.design, self.levels, self.cfg, assets, geoms)
        return "".join(geoms[i] for i in self.static), "".join(level_body(L, geoms) for L in self.levels)

    def contact_xml(self):
        """Driven trays never collide with each other or with the lab."""
        names = ["world"] + [L["name"] for L in self.levels]
        pairs = [(a, b) for i, a in enumerate(names) for b in names[i + 1:]]
        return "<contact>" + "".join(f'<exclude body1="{a}" body2="{b}"/>' for a, b in pairs) + "</contact>"

    def bind(self, m):
        """Hinge addresses and body ids in a compiled model."""
        self.body = np.array([m.body(L["name"]).id for L in self.levels])
        jnt = [m.joint(L["name"]).id for L in self.levels]
        self.qadr, self.dadr = m.jnt_qposadr[jnt], m.jnt_dofadr[jnt]
        self.amp = np.array([L["amp_rad"] for L in self.levels])
        self.vamp = np.radians(self.cfg["vib_deg"]) * np.sign(self.amp)
        return self

    # ---------- every step ----------
    def drive(self, d, i):
        """Write every hinge's angle and angular velocity for step i (counted from the start of the settle)."""
        i = min(i, len(self.f) - 1)
        d.qpos[self.qadr] = self.amp * self.f[i] + self.vamp * self.g[i]
        d.qvel[self.dadr] = self.amp * self.df[i] + self.vamp * self.dg[i]

    def vib_axis(self):
        """Unit direction of the tower's buzz (sorter.py's stroke axis)."""
        th = np.radians(self.cfg["vib_angle_deg"])
        return np.array([np.cos(th), 0.0, np.sin(th)])

    def vibration(self, n_shake, dt):
        """The buzz as a translation stroke: displacement, velocity and acceleration along vib_axis() at each of
        n_shake steps after the settle (sorter.py prepends the settle's zeros). All zero when vib_mm is 0."""
        A, w = self.cfg["vib_mm"], 2 * np.pi * self.cfg["vib_hz"]
        t = np.arange(n_shake) * dt
        return A * np.sin(w * t), A * w * np.cos(w * t), -A * w * w * np.sin(w * t)

    def quats(self, d):
        """Each level's orientation in the lab, levels x 4 (w x y z)."""
        return d.xquat[self.body].astype(np.float32)

    def zone_frames(self, d):
        """(k, xyz) -> xyz in the rest frame of the level that holds design zone k, for sorter.assign_zones."""
        pos, mat = d.xpos[self.body].copy(), d.xmat[self.body].reshape(-1, 3, 3).copy()
        lev = [self.zone_level.get(z["name"]) for z in self.design.zones]

        def local(k, xyz):
            j = lev[k]
            return xyz if j is None else (xyz - pos[j]) @ mat[j]
        return local

    def widen(self, bounds):
        """sorter's lost-particle bounds, grown to cover every level's box geoms at full tilt both ways."""
        lo, hi = (np.array(b, dtype=float) for b in bounds)
        for L in self.levels:
            p = np.array(L["pivot"])
            for i in L["geoms"]:
                g = self.design.geoms[i]
                if g["type"] != "box":
                    continue
                c = np.array(g["pos"]) + np.array(np.meshgrid(*[(-s, s) for s in g["size"]])).reshape(3, -1).T
                th_max = abs(L["amp_rad"]) + np.radians(self.cfg["vib_deg"])
                for th in (th_max, -th_max):
                    r = (c - p) @ rot_y(th).T + p
                    pad = 5.0 + self.cfg["vib_mm"]
                    lo, hi = np.minimum(lo, r.min(axis=0) - pad), np.maximum(hi, r.max(axis=0) + pad)
        return lo, hi

    # ---------- reporting ----------
    def scene_levels(self, m):
        """scene["levels"]: per level its pivot (mm, tray frame = lab at rest), hinge axis, phase sign, amplitude,
        the zone it holds, its MuJoCo body and geom ids, and "geoms": indices into scene["tray"]["geoms"]
        (sorter.scene_geoms, which leaves the lids out)."""
        drawn = {i: j for j, i in enumerate(i for i, g in enumerate(self.design.geoms) if g["role"] != "lid")}
        return [{"name": L["name"], "zone": L["zone"], "pivot": L["pivot"], "axis": [0.0, 1.0, 0.0], "sign": L["sign"],
                 "amp_deg": round(float(np.degrees(L["amp_rad"])), 4), "body_id": int(b),
                 "mj_geom_ids": [int(m.geom(f"tray{i}").id) for i in L["geoms"]],
                 "geoms": [drawn[i] for i in L["geoms"] if i in drawn]}
                for L, b in zip(self.levels, self.body)]

    def summary(self):
        vib_g = self.cfg["vib_mm"] * (2 * np.pi * self.cfg["vib_hz"]) ** 2 / G
        return {**self.cfg, "vib_peak_g": round(float(vib_g), 3), "axis": "y", "levels": [{"zone": L["zone"], "pivot": L["pivot"], "sign": L["sign"],
                                                     "amp_deg": round(float(np.degrees(L["amp_rad"])), 4)}
                                                    for L in self.levels],
                "pitch_mm": self.design.info.get("pitch_mm"), "clearance": self.clear}


def level_body(L, geoms):
    p = " ".join(f"{c:.4f}" for c in L["pivot"])
    return (f'<body name="{L["name"]}" pos="0 0 0">'
            f'<joint name="{L["name"]}" type="hinge" pos="{p}" axis="0 1 0" armature="{LEVEL_INERTIA:g}"/>'
            f'<inertial pos="{p}" mass="{LEVEL_MASS:g}" diaginertia="{LEVEL_INERTIA:g} {LEVEL_INERTIA:g} {LEVEL_INERTIA:g}"/>'
            + "".join(geoms[i] for i in L["geoms"]) + "</body>")


def tray_geoms(design, tray):
    """sorter.tray_xml's geoms string -> one <geom/> element per design geom, in order."""
    geoms = re.findall(r"<geom [^>]*/>", tray)
    if len(geoms) != len(design.geoms):
        raise RuntimeError(f"rocking: {len(geoms)} tray geoms in the XML, {len(design.geoms)} in the design")
    return geoms


def clearance(design, levels, cfg, assets, geoms, samples=CLEARANCE_SAMPLES, distmax=60.0):
    """Closest approach between neighbouring levels over one cycle (the invisible lids left out), in mm;
    negative means the boxes overlap. The trays only move by their prescribed angles, so this is exact.
    assets, geoms: sorter.tray_xml's meshes and its geoms split by tray_geoms()."""
    sub = [{"name": L["name"], "pivot": L["pivot"], "geoms": [i for i in L["geoms"] if design.geoms[i]["role"] != "lid"]}
           for L in levels]
    m = mujoco.MjModel.from_xml_string(f'<mujoco><asset>{assets}</asset><worldbody>'
                                       f'{"".join(level_body(L, geoms) for L in sub)}</worldbody></mujoco>')
    d = mujoco.MjData(m)
    amp = np.radians(cfg["deg"] + cfg.get("vib_deg", 0.0))
    signs = [(-1) ** k if cfg["alternate"] else 1 for k in range(len(levels))]
    if not cfg["catch"]:
        signs[-1] = 0
    ids = [np.array([m.geom(f"tray{i}").id for i in L["geoms"]]) for L in sub]
    out = []
    for k in range(len(sub) - 1):
        best = (np.inf, None, None)
        for f in np.linspace(-1.0, 1.0, samples):
            d.qpos[:] = [s * amp * f for s in signs]
            mujoco.mj_kinematics(m, d)
            a, b = ids[k], ids[k + 1]
            gap = (np.linalg.norm(d.geom_xpos[a][:, None] - d.geom_xpos[b][None], axis=2)
                   - m.geom_rbound[a][:, None] - m.geom_rbound[b][None])
            for i, j in zip(*np.nonzero(gap < distmax)):
                dist = mujoco.mj_geomDistance(m, d, int(a[i]), int(b[j]), distmax, None)
                if dist < best[0]:
                    best = (dist, round(float(np.degrees(amp * f * signs[k])), 2), (int(a[i]), int(b[j])))
        roles = [design.geoms[int(m.geom(g).name[4:])]["role"] for g in best[2]] if best[2] else None
        out.append({"upper": levels[k]["zone"], "lower": levels[k + 1]["zone"],
                    "min_mm": round(float(best[0]), 2) if np.isfinite(best[0]) else None,
                    "at_upper_deg": best[1], "roles": roles})
    worst = min((c["min_mm"] for c in out if c["min_mm"] is not None), default=None)
    return {"pairs": out, "min_mm": worst, "touching": worst is not None and worst <= 0.0}


def with_pitch(spec, pitch):
    kind, _, arg = spec.partition(":")
    parts = [a for a in arg.split(",") if a and not a.startswith("pitch=")]
    return f"{kind}:{','.join(parts)},pitch={pitch:g}"


def without_tab(design):
    """The design with every geom lying wholly beyond the boxes' +X walls taken out: the mounting tab, which a
    seesaw pivoting across the middle may not need, and which sets the pitch."""
    def x_range(g):
        if g["type"] == "mesh":
            xs = [v[0] for v in g["vertices"]]
            return min(xs), max(xs)
        return g["pos"][0] - g["size"][0], g["pos"][0] + g["size"][0]
    x_wall = max(x_range(g)[1] for g in design.geoms if g["role"] == "wall")
    return dataclasses.replace(design, geoms=[g for g in design.geoms if x_range(g)[0] < x_wall - 1e-6])


def design_clearance(design, cfg):
    """clearance() for a design on its own, outside a run."""
    import sorter
    assets, tray = sorter.tray_xml(design)
    return clearance(design, find_levels(design)[0], cfg, assets, tray_geoms(design, tray))


def pitch_needed(spec, cfg, clear_mm=0.0, tab=True, lo=None, hi=300.0, tol=0.25):
    """Smallest pitch (box bottom to box bottom, mm) whose neighbouring boxes stay clear_mm apart over the cycle."""
    import designs

    def gap(p):                                  # None: farther apart than clearance() looks
        dsg = designs.build(with_pitch(spec, p))
        g = design_clearance(dsg if tab else without_tab(dsg), cfg)["min_mm"]
        return np.inf if g is None else g

    if lo is None:
        z0, z1 = designs.build(with_pitch(spec, 1000.0)).info["layers"][0]["holder_z_mm"]
        lo = z1 - z0 + 0.5
    if gap(hi) < clear_mm:
        raise ValueError(f"even {hi:g} mm doesn't clear {clear_mm:g} mm")
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) < clear_mm else (lo, mid)
    return round(hi, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("design", nargs="?", default="inserts:5mm,2mm,pitch=110")
    ap.add_argument("--deg", default="20,25,30", help="amplitudes to check, degrees")
    ap.add_argument("--clear", type=float, default=5.0, help="clearance to find the pitch for, mm")
    args = ap.parse_args()
    import designs
    dsg = designs.build(args.design)
    for deg in map(float, args.deg.split(",")):
        cfg = {**DEFAULTS, "deg": deg}
        c = design_clearance(dsg, cfg)
        print(f"{dsg.name} at +/-{deg:g} deg: closest {c['min_mm']} mm" + ("  TOUCHING" if c["touching"] else ""))
        for p in c["pairs"]:
            print(f"    {p['upper']} over {p['lower']}: {p['min_mm']} mm (upper at {p['at_upper_deg']} deg, {p['roles']})")
        for tab in (True, False):
            print(f"    pitch {'with the +X tab' if tab else 'without the tab'}: touching at "
                  f"{pitch_needed(args.design, cfg, 0.0, tab)} mm, {args.clear:g} mm clear at "
                  f"{pitch_needed(args.design, cfg, args.clear, tab)} mm")


if __name__ == "__main__":
    main()
