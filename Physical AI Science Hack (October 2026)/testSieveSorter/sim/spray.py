"""Spray model: fixed nozzles push, wet and stick particles. No fluid solver, no droplets.

Run from sim\\ to print the magnitude sanity table:  python spray.py

The bench sprays liquid from stationary nozzles onto specimens on a horizontally shaken tray. We model
that from measurements, as four effects on each particle body:

1. Push. A jet of flow Q through a nozzle of diameter d leaves at v0 = Q / (pi d^2 / 4) and carries
   momentum flux M = rho Q v0. It spreads in a cone: at axial distance s the footprint radius is
   R(s) = d/2 + s tan(half_angle), and the flux over that plane is a Gaussian with sigma =
   R / footprint_sigmas, normalised so it integrates to M on every plane (momentum is conserved;
   decay_mm > 0 lets it fade as exp(-s / decay_mm), modelling droplets slowing in air). No flux past
   range_mm. Each particle geom gets F = cd * q * A_proj along the jet axis, at its centre, so off-centre
   geoms also get a torque. q uses the droplet speed relative to the geom centre's lab velocity,
   q = rho * phi * (v - v_geom.u)^2 / v, so a jet can't push a body faster than its own droplets, and a
   multi-geom body spinning in the jet is braked rather than spun up without limit.
   A_proj is the geom's shadow area on a plane normal to the jet, in the geom's world orientation
   (see projected_area). The radial spread of the cone (up to sin(half_angle) of the force) is ignored.
   Shadowing is off by default: every geom in the footprint is hit. Setting shadow=True drops the push
   (and the wetting) of a geom when a ray from the nozzle to its centre first hits a different particle
   body (mujoco.mj_multiRay, particles only). Tray geoms never shadow, so a jet reaches through the tray.
   The nozzle is fixed in the LAB frame, so in sim (tray) coordinates it sits at pos_lab - tray_d(t).
2. Pulses. Jet.pulse = (on_s, off_s) switches it, starting "on" at t = 0. Each time a jet switches on,
   its flux ramps up linearly over ramp_s (10 ms is roughly the liquid's travel time over 60 mm). The
   ramp is also a numerical guard: at dt 5e-4, MuJoCo soft contacts let a 0.5 mm sphere hit by a SUDDEN
   force above about 200 x its weight tunnel through a 2 mm floor (100 x at timeconst 0.005), with no
   spray involved, while they hold the same load if it builds up gradually. Narrow jets on light
   particles reach those loads.
3. Wetness w in [0, 1] per particle body (self.wet, zero for other bodies). It follows
   dw/dt = phi / wet_film_mm * (1 - w) - w / dry_tau_s, where phi (mm/s) is the liquid volume flux at
   the body's wettest geom, integrated exactly each step.
4. Wet contact. Particle geoms carry the contact parameters (priority 1), so per step:
   - friction: geom_friction[g, 0] = mu_dry * (1 + (wet_friction_scale - 1) * w). The default of 1.0
     means no change, because the bench hasn't told us yet whether wet means slippier or grippier.
   - capillary adhesion: F = adhesion_scale * 2 pi gamma R_eff w, per contact, where gamma = 72 (water) or
     22 (ethanol) g/s^2, and R_eff is the geometric mean of the geom's two largest semi-extents
     (r for a sphere). The contact angle (cos theta, low for water on PLA, about 1 for ethanol) is folded
     into adhesion_scale, which the wet tilt test sets.
   - optional damping: F = -m * wet_damping_per_s * w * v, with v the body's velocity relative to the tray.

Why geom adhesion and not adhesion actuators: MuJoCo 3.17 has both. An <adhesion> actuator applies a total
force ctrl * gain to one body, split equally between every contact of that body's geoms, and only while
those contacts exist (without gap, only active ones). That models a vacuum gripper. A capillary bridge is a
passive, per-contact property, and the MuJoCo docs point to geom/adhesion for exactly that: each contact
can pull with up to `adhesion` before breaking, its friction budget becomes mu * (f_N + adhesion), and
resting penetration is unchanged. With actuators, a grain bridging two sieve bars would get half the force
per bar, a grain in a pile would get almost none at the wall, child bodies (hinged parts) would get none,
and mj_transmission would cost O(actuators x contacts) every step. So step() writes model.geom_adhesion
for particle geoms. Because the compiler sets model.flg_adhesion only when some geom has adhesion > 0,
__init__ switches it on. That flag is only a fast-path guard in mj_passive and the constraint
builder. A contact's adhesion is the particle geom's value against the tray (higher priority wins) and
the sum of both values between two particles. With the default adhesion_reach_mm = 0, adhesion acts only
on touching contacts. That is enough for friction (the wet tilt test) but not for pull-off. Setting it
> 0 (e.g. 0.1) raises geom_gap of particle geoms, so MuJoCo detects contacts out to that distance: wet
ones pull, like a meniscus holding a bouncing grain, and dry ones stay inactive. Particle pairs get twice
the reach, because gaps add. The extra contacts make mj_step about 45% slower in the pool scene, even
dry. mjcf_extras therefore returns "".
Measured in scratch tests: a rice-sized ellipsoid on a 30 deg tilt (mu 0.4) slides with adhesion off
and holds at full wetness. With reach > 0, pull-off resistance works for spheres; a flat ellipsoid pulled
straight up tips onto its end and lets go, which is a limit of the single-point contact.

Magnitude sanity (water, 5 mL/s, 1 mm nozzle, half angle 15 deg, footprint_sigmas 2, 60 mm away, on axis):
  v0 = 6.37 m/s, M = rho Q v0 = 31.8 mN; footprint radius 16.6 mm, sigma 8.3 mm, peak q = 73.7 Pa
  long rice grain, 17 mg (weight 0.167 mN), ellipsoid 6.5 x 2 x 1.7 mm:
    jet from above, lying flat: A 10.2 mm^2, F 0.75 mN = 4.5 x weight
    jet from the side, broadside: A 8.7 mm^2, F 0.64 mN = 3.8 x weight; end-on: 2.7 mm^2, 1.2 x weight
    capillary 2 pi gamma R_eff at w = 1 (R_eff 1.80 mm): 0.82 mN = 4.9 x weight
  3 mm fly, 3 mg (weight 0.029 mN), body as ellipsoid 3 x 1.4 x 1.2 mm, wings and legs not counted:
    jet from above: A 3.3 mm^2, F 0.24 mN = 8.3 x weight
    capillary at w = 1 (R_eff 1.02 mm): 0.46 mN = 16 x weight
  So a cone spray dominates gravity for everything in the footprint core. A coherent 1 mm stream (no cone)
  would put up to the whole 31.8 mN (190 x a rice grain's weight) on whatever it hits, so the measured
  footprint matters most. In 3 s of the pool sorter with its default jets, 8 of 30 rice grains left the
  load zone with these defaults, 10 with adhesion_scale 0 and 3 with no spray. Adding adhesion_reach_mm
  0.1 glued wet grains (1 left). So adhesion_scale must come from the wet tilt test.
"""
import csv
from dataclasses import dataclass

import mujoco
import numpy as np

PARAMS = {
    "cd": 1.0,                  # -, fraction of the intercepted jet momentum flux passed to a geom (1 = droplets stop on it)
    "footprint_sigmas": 2.0,    # -, cone edge (half_angle_deg) in Gaussian sigmas off the axis (2: 86% of flux inside)
    "decay_mm": 0.0,            # mm, e-folding length of momentum flux with distance from the nozzle; 0 = no decay
    "wet_film_mm": 0.05,        # mm, liquid depth delivered per unit area that takes a dry body to 63% wet
    "dry_tau_s": 30.0,          # s, drying time constant of w outside the spray
    "wet_friction_scale": 1.0,  # -, mu_wet / mu_dry at w = 1 (< 1 slippier, > 1 grippier)
    "adhesion_scale": 0.1,      # -, multiplies the capillary estimate 2 pi gamma R_eff w per contact; 0 = no adhesion.
                                # Full strength (1.0) glues small wet particles down; 0.1 until the wet tilt test sets it
    "adhesion_reach_mm": 0.0,   # mm, particle geom gap: wet contacts pull across it (0.1: mj_step ~45% slower)
    "wet_damping_per_s": 0.0,   # 1/s, drag on a wet body's velocity relative to the tray, F = -m c w v
    "shadow": False,            # bool, a geom hidden from the nozzle by another particle body gets no push or wetting
    "ramp_s": 0.01,             # s, a jet's flux ramps up linearly over this after it switches on (travel, valve)
}
LIQUIDS = {"water": {"rho": 1.0e-3, "gamma": 72.0},     # g/mm^3, g/s^2 (= mN/m)
           "ethanol": {"rho": 0.79e-3, "gamma": 22.0}}


@dataclass
class Jet:
    pos_lab: tuple          # nozzle position, mm, lab frame (tray frame at rest)
    dir: tuple              # unit direction
    flow_ml_s: float = 5.0
    nozzle_d_mm: float = 1.0
    half_angle_deg: float = 15.0
    range_mm: float = 150.0
    pulse: tuple | None = None   # (on_s, off_s)
    liquid: str = "water"        # water | ethanol


def jets_from_csv(path):
    """Jet kwargs from the bench's jets.csv (BENCH.md step 7); rows starting with # are skipped."""
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if not r["jet_id"] or r["jet_id"].startswith("#"):
            continue
        tilt, az = np.radians(float(r["tilt_from_down_deg"] or 0)), np.radians(float(r["azimuth_deg"] or 0))
        jet = {"pos_lab": (float(r["x_mm"]), float(r["y_mm"]), float(r["z_mm"])),
               "dir": (np.sin(tilt) * np.cos(az), np.sin(tilt) * np.sin(az), -np.cos(tilt)),
               "flow_ml_s": float(r["collected_ml"]) / float(r["collect_s"]),
               "nozzle_d_mm": float(r["nozzle_d_mm"]), "liquid": r["liquid"] or "water"}
        if r["footprint_d_mm"] and r["footprint_height_mm"]:
            jet["half_angle_deg"] = float(np.degrees(np.arctan(float(r["footprint_d_mm"]) / 2 / float(r["footprint_height_mm"]))))
        if r["pulse_on_s"] and r["pulse_off_s"]:
            jet["pulse"] = (float(r["pulse_on_s"]), float(r["pulse_off_s"]))
        out.append(jet)
    return out


def jet_constants(jet):
    """Exit speed v0 (mm/s), volume flow Q (mm^3/s), density, momentum flux M = rho Q v0 (g mm/s^2)."""
    q = jet.flow_ml_s * 1000.0
    v0 = q / (np.pi * jet.nozzle_d_mm ** 2 / 4)
    rho = LIQUIDS[jet.liquid]["rho"]
    return v0, q, rho, rho * q * v0


def shape_coeffs(gtype, size, aabb_half):
    """Per-geom coefficients for projected_area, and the capillary radius R_eff (mm).

    MuJoCo sizes: sphere [r], capsule [r, half_len] and cylinder [r, half_len] along local z,
    ellipsoid [rx, ry, rz], box [hx, hy, hz]. Other types (meshes) fall back to their local AABB box.
    """
    n = len(gtype)
    c = {k: np.zeros(n) for k in ("iso", "side", "disc")}
    c["ell"], c["box"] = np.zeros((n, 3)), np.zeros((n, 3))
    ext = aabb_half.copy()
    r, h = size[:, 0], size[:, 1]
    T = mujoco.mjtGeom
    sph, cap, cyl = gtype == T.mjGEOM_SPHERE, gtype == T.mjGEOM_CAPSULE, gtype == T.mjGEOM_CYLINDER
    ell = gtype == T.mjGEOM_ELLIPSOID
    box = ~(sph | cap | cyl | ell)
    c["iso"][sph | cap] = np.pi * r[sph | cap] ** 2
    c["side"][cap | cyl] = 4 * r[cap | cyl] * h[cap | cyl]
    c["disc"][cyl] = np.pi * r[cyl] ** 2
    a = size[ell]
    c["ell"][ell] = np.stack([a[:, 1] * a[:, 2], a[:, 0] * a[:, 2], a[:, 0] * a[:, 1]], axis=1)
    b = np.where(gtype[:, None] == T.mjGEOM_BOX, size, aabb_half)[box]
    c["box"][box] = 4 * np.stack([b[:, 1] * b[:, 2], b[:, 0] * b[:, 2], b[:, 0] * b[:, 1]], axis=1)
    ext[sph] = r[sph, None]
    ext[cap] = np.stack([r[cap], r[cap], r[cap] + h[cap]], axis=1)
    ext[cyl] = np.stack([r[cyl], r[cyl], h[cyl]], axis=1)
    ext[ell] = size[ell]
    ext[box] = b
    top2 = np.sort(ext, axis=1)[:, 1:]
    return c, np.sqrt(top2[:, 0] * top2[:, 1])


def projected_area(c, v):
    """Shadow area (mm^2) of each geom on a plane normal to v; v (..., n, 3) is the unit direction in each geom's frame.

    sphere pi r^2; ellipsoid pi sqrt((b c vx)^2 + (a c vy)^2 + (a b vz)^2); box 4 (hy hz |vx| + hx hz |vy| + hx hy |vz|);
    cylinder pi r^2 |vz| + 4 r h sin; capsule pi r^2 + 4 r h sin, where sin = sqrt(1 - vz^2).
    """
    av = np.abs(v)
    vz = av[..., 2]
    ev = c["ell"] * v
    return (c["iso"] + np.pi * np.sqrt((ev * ev).sum(-1)) + (c["box"] * av).sum(-1)
            + c["side"] * np.sqrt(np.maximum(1.0 - vz * vz, 0.0)) + c["disc"] * vz)


def _cross(a, b):
    """Row-wise cross product of (n, 3) arrays; much cheaper than np.cross for small n."""
    return a[:, _I1] * b[:, _I2] - a[:, _I2] * b[:, _I1]


_I1, _I2 = [1, 2, 0], [2, 0, 1]


class Spray:
    def __init__(self, model, data, jets, particle_bodies, params=None):
        self.p = {**PARAMS, **(params or {})}
        self.jets = [j if isinstance(j, Jet) else Jet(**j) for j in jets]
        # jets as arrays, one row each, so step() handles all jets in one pass
        u = np.array([j.dir for j in self.jets], float).reshape(-1, 3)
        const = np.array([jet_constants(j) for j in self.jets]).reshape(-1, 4)
        self._J = {"pos": np.array([j.pos_lab for j in self.jets], float).reshape(-1, 3),
                   "u": u / np.linalg.norm(u, axis=1, keepdims=True),
                   "v0": const[:, :1], "Q": const[:, 1:2], "rhoQ": const[:, 2:3] * const[:, 1:2],
                   "gamma": np.array([[LIQUIDS[j.liquid]["gamma"]] for j in self.jets]).reshape(-1, 1),
                   "r0": np.array([[j.nozzle_d_mm / 2] for j in self.jets]).reshape(-1, 1),
                   "tan": np.tan(np.radians([[j.half_angle_deg] for j in self.jets])).reshape(-1, 1),
                   "range": np.array([[j.range_mm] for j in self.jets], float).reshape(-1, 1),
                   "on_s": np.array([j.pulse[0] if j.pulse else np.inf for j in self.jets]),
                   "period": np.array([sum(j.pulse) if j.pulse else np.inf for j in self.jets])}

        # every body of every particle (roots and their children), and their geoms grouped by body
        roots = np.unique(model.body_rootid[np.asarray(particle_bodies, int)])
        pbody = np.flatnonzero(np.isin(model.body_rootid, roots) & (np.arange(model.nbody) > 0))
        pg = np.flatnonzero(np.isin(model.geom_bodyid, pbody))
        self.pg = pg[np.argsort(model.geom_bodyid[pg], kind="stable")]
        gb = model.geom_bodyid[self.pg]
        self.ub, self.starts = np.unique(gb, return_index=True)    # bodies with geoms; first geom of each
        self.gl = np.searchsorted(self.ub, gb)                     # geom -> index into ub
        self.gb = gb
        self.ub_root = model.body_rootid[self.ub]
        self.mass = model.body_mass[self.ub].copy()
        self.coef, self.reff = shape_coeffs(model.geom_type[self.pg], model.geom_size[self.pg],
                                            model.geom_aabb[self.pg, 3:])
        self.mu_dry = model.geom_friction[self.pg, 0].copy()
        self.wet = np.zeros(model.nbody)
        self._w = np.zeros(len(self.ub))
        self._gamma = np.full(len(self.ub), self._J["gamma"][0, 0] if self.jets else LIQUIDS["water"]["gamma"])
        self._t_prev = None
        if self.p["adhesion_scale"] > 0 and len(self.pg):
            model.geom_gap[self.pg] = np.maximum(model.geom_gap[self.pg], self.p["adhesion_reach_mm"])
            model.flg_adhesion = True

    @staticmethod
    def mjcf_extras(particle_body_names, params=None):
        """No extra MJCF: adhesion uses geom_adhesion, set at runtime (see module docstring)."""
        return ""

    def _body_vel(self, data):
        """Angular velocity and CoM linear velocity (n_bodies, 3) of each particle body, sim (tray) frame."""
        cv = data.cvel[self.ub]
        arm = data.xipos[self.ub] - data.subtree_com[self.ub_root]
        return cv[:, :3], cv[:, 3:] + _cross(cv[:, :3], arm)

    def _visible(self, model, data, nozzle, x, idx):
        """True for geoms idx whose ray from the nozzle first hits their own body (or nothing)."""
        vec = x[idx] - nozzle
        vec /= np.linalg.norm(vec, axis=1, keepdims=True)
        hit = np.empty(len(idx), np.int32)
        dist = np.empty(len(idx))
        mujoco.mj_multiRay(model, data, nozzle, vec.ravel(), None, False, -1, hit, dist, None, len(idx), 1e9)
        return (hit < 0) | (model.geom_bodyid[np.maximum(hit, 0)] == self.gb[idx])

    def _push(self, model, data, t, tray_d, v_lab, x):
        """Jet force magnitude and liquid volume flux phi (mm/s), both (n_jets, n_geoms), or None if no jet reaches."""
        J, p = self._J, self.p
        nozzle = J["pos"] - tray_d                                    # sim frame
        rel = x[None] - nozzle[:, None]                               # (jets, geoms, 3)
        s = np.einsum("kni,ki->kn", rel, J["u"])                      # axial distance
        phase = t % J["period"]                                       # time since this jet last switched on
        on = (phase < J["on_s"]) * (np.clip(phase / p["ramp_s"], 0.0, 1.0) if p["ramp_s"] > 0 else 1.0)
        inside = (s > 0) & (s < J["range"]) & (on > 0)[:, None]
        if not inside.any():
            return None
        s = np.where(inside, s, 1.0)
        sig = (J["r0"] + s * J["tan"]) / p["footprint_sigmas"]
        r2 = np.einsum("kni,kni->kn", rel, rel) - s * s
        prof = np.where(inside, np.exp(-r2 / (2 * sig * sig)) / (2 * np.pi * sig * sig), 0.0) * on[:, None]  # 1/mm^2
        v = J["v0"] * np.exp(-s / p["decay_mm"]) if p["decay_mm"] > 0 else J["v0"]
        w_rel = np.maximum(v - np.einsum("ni,ki->kn", v_lab, J["u"]), 0.0)
        rot = data.geom_xmat[self.pg].reshape(-1, 3, 3)
        area = projected_area(self.coef, np.einsum("ki,nij->knj", J["u"], rot))
        mag = p["cd"] * J["rhoQ"] * prof * w_rel * w_rel / v * area
        if p["shadow"]:
            for k in range(len(mag)):
                idx = np.flatnonzero(mag[k] > 0)
                if len(idx):
                    hidden = idx[~self._visible(model, data, nozzle[k], x, idx)]
                    mag[k, hidden] = 0.0
                    prof[k, hidden] = 0.0
        return mag, J["Q"] * prof

    def step(self, model, data, t, tray_d, tray_v):
        p = self.p
        if not len(self.pg):
            return
        dt = model.opt.timestep if self._t_prev is None else max(t - self._t_prev, 0.0)
        self._t_prev = t
        omega, v_sim = self._body_vel(data)
        phi = gamma = None
        if self.jets:
            x = data.geom_xpos[self.pg]
            arm = x - data.xipos[self.gb]
            v_lab = v_sim[self.gl] + _cross(omega[self.gl], arm) + tray_v      # each geom centre, lab frame
            out = self._push(model, data, t, np.asarray(tray_d, float), v_lab, x)
            if out is not None:
                mag, phik = out
                force = mag.T @ self._J["u"]
                ft = np.concatenate([force, _cross(arm, force)], axis=1)
                data.xfrc_applied[self.ub] += np.add.reduceat(ft, self.starts, axis=0)
                phi = phik.sum(0)
                gamma = (self._J["gamma"] * phik).sum(0)

        # wetness: exact update of dw/dt = a (1 - w) - b w over dt
        a = np.maximum.reduceat(phi, self.starts) / p["wet_film_mm"] if phi is not None else 0.0
        b = 1.0 / p["dry_tau_s"]
        w_eq = a / (a + b)
        self._w = w_eq + (self._w - w_eq) * np.exp(-(a + b) * dt)
        self.wet[self.ub] = self._w
        if phi is not None and len(self.jets) > 1:                    # liquid on each body, flux-weighted
            sprayed = a > 0
            self._gamma[sprayed] = (np.add.reduceat(gamma, self.starts)[sprayed]
                                    / np.add.reduceat(phi, self.starts)[sprayed])

        w_g = self._w[self.gl]
        if p["wet_friction_scale"] != 1.0:
            model.geom_friction[self.pg, 0] = self.mu_dry * (1 + (p["wet_friction_scale"] - 1) * w_g)
        if p["adhesion_scale"] > 0:
            model.geom_adhesion[self.pg] = p["adhesion_scale"] * 2 * np.pi * self._gamma[self.gl] * self.reff * w_g
        if p["wet_damping_per_s"] > 0:
            data.xfrc_applied[self.ub, :3] -= (self.mass * p["wet_damping_per_s"] * self._w)[:, None] * v_sim


def _sanity(flow_ml_s=5.0, nozzle_d_mm=1.0, half_angle_deg=15.0, s=60.0):
    """Print jet force and capillary force against weight for a rice grain and a fly."""
    jet = Jet((0, 0, 0), (0, 0, -1), flow_ml_s, nozzle_d_mm, half_angle_deg)
    v0, q, rho, mflux = jet_constants(jet)
    R = nozzle_d_mm / 2 + s * np.tan(np.radians(half_angle_deg))
    sig = R / PARAMS["footprint_sigmas"]
    q0 = mflux / (2 * np.pi * sig ** 2)
    print(f"water {flow_ml_s} mL/s, {nozzle_d_mm} mm nozzle, {half_angle_deg} deg, {s} mm away, on axis:")
    print(f"  v0 {v0/1000:.2f} m/s, momentum flux {mflux/1000:.1f} mN, footprint radius {R:.1f} mm, "
          f"sigma {sig:.2f} mm, peak q {q0:.1f} Pa")
    E = mujoco.mjtGeom.mjGEOM_ELLIPSOID
    for name, mass_mg, semi in (("rice", 17.0, (3.25, 1.0, 0.85)), ("fly", 3.0, (1.5, 0.7, 0.6))):
        c, reff = shape_coeffs(np.array([E]), np.array([semi]), np.array([semi]))
        weight = mass_mg * 1e-3 * 9810
        cap = 2 * np.pi * LIQUIDS["water"]["gamma"] * reff[0]
        print(f"  {name} {mass_mg} mg, weight {weight/1000:.3f} mN, capillary at w=1 {cap/1000:.2f} mN "
              f"= {cap/weight:.1f} x weight (R_eff {reff[0]:.2f} mm)")
        for view, v in (("from above", (0, 0, 1)), ("broadside", (0, 1, 0)), ("end-on", (1, 0, 0))):
            area = projected_area(c, np.array([v], float))[0]
            f = PARAMS["cd"] * q0 * area
            print(f"    jet {view:10s}: area {area:5.2f} mm^2, force {f/1000:.3f} mN = {f/weight:4.1f} x weight")


if __name__ == "__main__":
    _sanity()
