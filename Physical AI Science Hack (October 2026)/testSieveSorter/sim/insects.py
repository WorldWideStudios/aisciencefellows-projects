"""Preserved insect specimens for the sorter sim, as compound rigid bodies. Units mm, g, s.

make(kind, rng, size_scale=1.0) -> common.Particle, for kind in KINDS:
  insect_compact   beetle, mite                      dark brown
  insect_elongate  fly, wasp, ant                    near-black / grey
  insect_longleg   mosquito (or midge), crane fly, spider   tan
Each specimen is ONE rigid body with no joints: x points forward, y left and z up, and the origin
sits at the centre of the body (head + thorax + abdomen). Head, thorax and abdomen are
ellipsoids. Each leg is two capsules, femur and tibia+tarsus, at an angle. Antennae are capsules
and wings are thin translucent ellipsoids. Spiders and mites have 8 legs. Ants and wasps have a
petiole (a narrow waist). Specimens are passive. Leg folding is a pose drawn once per specimen:
splayed, folded, or a per-leg mix. Folded means tucked under the body for most insects, curled
over it for spiders and mites, and trailing along the body for mosquitoes and crane flies. Damage
is drawn per specimen: missing legs, legs broken at the knee, missing antennae, one or both wings
missing, and wings spread or folded. Beetles sometimes have the elytra open.

Sizes: body length L (head to abdomen tip, without appendages) is lognormal per body plan,
resampled until it falls in [min, max] (table PLANS). Malaise-trap catches are dominated by small
Diptera. In Srivathsan et al. 2023, Nat Ecol Evol 7:1012-1021 (39 traps, 8 countries, 225k
specimens), ten families hold about 62% of the specimens in each trap. Gall midges
(Cecidomyiidae) alone are about 20% of the species per site, and the top 20 families include
Phoridae, Chironomidae, Sciaridae and Ceratopogonidae, all about 1-4 mm. The paper gives no
length histogram, so the medians and spreads below are ASSUMPTIONS taken from textbook adult
lengths, not a fit:
  small flies 1-4 mm, parasitoid wasps 1-5, ants 2-10, beetles 1-10, mites 0.3-1.5,
  spiders 1-10, mosquitoes and midges 2-6, crane flies 5-20 (Limoniidae small, Tipula large).
Leg length / L: beetle 0.5-0.75, fly 0.6-1.0, wasp and ant 0.7-1.0, spider 0.8-1.8, mosquito
1.3-2.0, crane fly 1.7-2.6. That gives mosquito and crane-fly leg spans of about 2-5 L when splayed.

Thin parts: leg and antenna capsules have a radius of at least LEG_R_MIN, and wings have a
half-thickness of WING_HT. When the radius is clamped, the leg density is lowered so the leg mass
still matches the real radius. Wing density is set so the wing mass matches a real membrane
(WING_AREAL). The body parts use RHO.

Stability, from scratch tests: 30 specimens shaken 5 s at 3 mm, 10 Hz on a floor and on a plate of
1 mm bars, with dt 5e-4, solref 0.005 1, solimp 0.95 0.99 0.0001 and friction 0.4. There were no NaNs
and no warnings, and body speeds stayed under 400 mm/s after landing. Legs down to r 0.02 and wings
down to 0.01 mm half-thickness were just as stable. The real limit is contact softness: a geom
that hits at speed v sinks about v * timeconst / e. Hits above roughly 400 mm/s pass the mid-plane
of a 1 mm bar, the contact normal flips, and the geom is pushed through. That happens to
long-legged specimens landing after a drop, and to a few leg strikes per 30 specimens per 5 s of
shaking. timeconst 0.002 removed it during shaking. LEG_R_MIN stays 0.06 so that legs still catch
on each other (leg-leg contact depth p99 is about 0.1 mm).

The real Malaise mix (new kinds insect_malaise, insect_malaise_lt2 / _2to6 / _gt6; MALAISE_MIX): body length
fitted to EntoSieve's counted Malaise samples, 57% under 1.5 mm. See the block above _make_malaise. KINDS and
PLANS are unchanged.

Run from sim\\:  python insects.py   (prints the size and geom summary of 2000 specimens per kind)
                python insects.py malaise   (the Malaise kinds: class shares, plan shares and geoms)
"""
import numpy as np

import common

KINDS = ("insect_compact", "insect_elongate", "insect_longleg")

RHO = 1.05e-3            # g/mm^3, body parts (fresh or ethanol-preserved insect tissue)
WING_AREAL = 4e-6        # g/mm^2, wing membrane (~3 um of cuticle)
LEG_R_MIN = 0.06         # mm, smallest capsule radius for legs and antennae (stability floor)
WING_HT = 0.04           # mm, wing half-thickness (stability floor; real wings are ~0.003)
OVERLAP = 0.12           # body segments overlap their neighbours by this fraction of their length
JIT = 0.08               # per-specimen proportion jitter (+-)
P_WINGS_GONE = 0.05      # both wings (or all four) missing
P_WING_ONE = 0.08        # one side's wings missing
P_ANTENNA_GONE = 0.10    # per antenna
P_LEG_BROKEN = 0.04      # per leg: tibia+tarsus gone, femur left
P_ELYTRA_OPEN = 0.08     # beetles

# plan: (weight within kind, median L mm, lognormal sigma, min L, max L)
PLANS = {
    "insect_compact": {"beetle": (0.65, 2.8, 0.50, 1.0, 15.0),
                       "mite": (0.35, 0.7, 0.35, 0.3, 2.0)},
    "insect_elongate": {"fly": (0.65, 2.3, 0.50, 0.8, 15.0),
                        "wasp": (0.15, 2.5, 0.55, 0.8, 18.0),
                        "ant": (0.20, 3.5, 0.40, 1.5, 15.0)},
    "insect_longleg": {"mosquito": (0.30, 3.5, 0.35, 1.5, 9.0),
                       "cranefly": (0.25, 8.0, 0.35, 4.0, 20.0),
                       "spider": (0.45, 2.2, 0.50, 0.8, 12.0)},
}
COLORS = {"insect_compact": (0.36, 0.21, 0.10),
          "insect_elongate": (0.20, 0.20, 0.23),
          "insect_longleg": (0.80, 0.64, 0.42)}
WING_RGBA = (0.82, 0.88, 0.95, 0.35)
LEG_SHADE = 0.8          # legs and antennae are a little darker than the body

D = np.pi / 180


def _rot(yaw=0.0, pitch=0.0, roll=0.0):
    """Rotation matrix and wxyz quaternion of Rz(yaw) Ry(pitch) Rx(roll)."""
    cy, sy, cp, sp, cr, sr = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch), np.cos(roll), np.sin(roll)
    R = (np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
         @ np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
         @ np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]]))
    h = 0.5 * np.array([yaw, pitch, roll])
    qz, qy, qx = ([np.cos(h[0]), 0, 0, np.sin(h[0])], [np.cos(h[1]), 0, np.sin(h[1]), 0],
                  [np.cos(h[2]), np.sin(h[2]), 0, 0])
    return R, _qmul(_qmul(qz, qy), qx)


def _qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


def _dir(yaw, elev, side):
    """Unit vector: yaw from +x towards the given side (+1 left, -1 right), elevation up from horizontal."""
    return np.array([np.cos(elev) * np.cos(yaw), side * np.cos(elev) * np.sin(yaw), np.sin(elev)])


def _u(rng, lo, hi):
    return rng.uniform(lo, hi)


class _Spec:
    """Geoms of one specimen, in the specimen frame, before centring."""

    def __init__(self, rgba):
        self.geoms, self.seg, self.notes = [], {}, []
        self.rgba = tuple(rgba) + (1.0,)
        self.leg_rgba = tuple(LEG_SHADE * c for c in rgba) + (1.0,)

    def ell(self, c, semi, R=None, q=None, dens=RHO, rgba=None, body=True, name=None):
        if R is None:
            R, q = np.eye(3), [1.0, 0.0, 0.0, 0.0]
        g = dict(type="ellipsoid", pos=np.array(c, float), size=np.array(semi, float), R=R, quat=q,
                 dens=dens, rgba=rgba or self.rgba, body=body)
        self.geoms.append(g)
        if name:
            self.seg[name] = g

    def cap(self, a, b, r, dens, rgba=None):
        a, b = np.array(a, float), np.array(b, float)
        if np.linalg.norm(b - a) < 1e-3:
            return
        self.geoms.append(dict(type="capsule", a=a, b=b, r=r, dens=dens, rgba=rgba or self.leg_rgba, body=False))

    def pt(self, seg, fx, fy, fz):
        """Point at fractional coordinates of a segment ellipsoid (1 = on its semi-axis)."""
        g = self.seg[seg]
        return g["pos"] + g["R"] @ (g["size"] * np.array([fx, fy, fz]))


def _segments(sp, rng, L, parts, wfac=1.0, tfac=1.0, abd_pitch=0.0, overlap=OVERLAP):
    """Body segments front to back along x, each (name, length, width, thickness, z) as fractions of L."""
    lens = np.array([p[1] for p in parts]) * rng.uniform(1 - JIT, 1 + JIT, len(parts))
    lens *= L / lens.sum()
    x = L / 2
    for i, ((name, _, wf, tf, zf), ln) in enumerate(zip(parts, lens)):
        a = ln / 2 * (1 + overlap)
        cx = x - a if i == 0 else (x - ln + a if i == len(parts) - 1 else x - ln / 2)
        b = wf * wfac * L / 2 * _u(rng, 1 - JIT, 1 + JIT)
        c = tf * tfac * L / 2 * _u(rng, 1 - JIT, 1 + JIT)
        R = q = None
        if i == len(parts) - 1 and abd_pitch:
            R, q = _rot(pitch=abd_pitch)
        sp.ell((cx, 0.0, zf * L), (a, b, c), R, q, name=name)
        x -= ln


def _leg_angles(rng, pose, yaw0, splay):
    """Femur (yaw, elev) and tibia (yaw, elev) in radians for one leg."""
    n = lambda s: rng.normal(0, s * D)
    if pose == "splayed":
        y1 = yaw0 + n(10)
        return y1, _u(rng, *splay[0]) * D, y1 + n(12), _u(rng, *splay[1]) * D
    if pose == "tucked":      # femur down and out, tibia folded back under the body
        y1 = 0.5 * (yaw0 + 90 * D) + n(10)
        return y1, -_u(rng, 35, 65) * D, y1 + _u(rng, 140, 175) * D, _u(rng, -20, 5) * D
    if pose == "trailing":    # long legs swept along the body: front pair forward, the rest back
        fwd = yaw0 < 60 * D
        y1 = _u(rng, *((10, 40) if fwd else (110, 160))) * D
        y2 = _u(rng, *((-5, 20) if fwd else (160, 185))) * D
        return y1, _u(rng, -15, 10) * D, y2, _u(rng, -15, 10) * D
    y1 = yaw0 + n(10)         # curled: femur up, tibia hooked back in and down (spiders, mites)
    return y1, _u(rng, 20, 55) * D, y1 + np.pi + n(20), -_u(rng, 45, 75) * D


def _legs(sp, rng, hips, r_real, poses, splay, p_miss, fold="tucked"):
    """hips: [(point, side, rest yaw in degrees, leg length)]. poses: probabilities of splayed, fold, mixed."""
    r = max(LEG_R_MIN, r_real)
    dens = RHO * min(1.0, (r_real / r) ** 2)
    pose = rng.choice(["splayed", fold, "mixed"], p=poses)
    lost = broken = 0
    for hip, side, yaw0, ln in hips:
        if rng.random() < p_miss:
            lost += 1
            continue
        leg_pose = pose if pose != "mixed" else rng.choice(["splayed", fold])
        y1, e1, y2, e2 = _leg_angles(rng, leg_pose, yaw0 * D, splay)
        f = _u(rng, 0.40, 0.48)
        knee = hip + f * ln * _dir(y1, e1, side)
        sp.cap(hip, knee, r, dens)
        if rng.random() < P_LEG_BROKEN:
            broken += 1
            continue
        sp.cap(knee, knee + (1 - f) * ln * _dir(y2, e2, side), r, dens)
    sp.notes.append(f"legs {pose} {len(hips) - lost}/{len(hips)}" + (f" broken {broken}" if broken else ""))


def _insect_hips(sp, rng, seg, leg_len, ratios, xs=(0.45, 0.0, -0.45), fy=0.5, fz=-0.55, yaws=(35, 90, 140)):
    out = []
    for fx, ratio, yaw in zip(xs, ratios, yaws):
        for side in (1, -1):
            out.append((sp.pt(seg, fx, side * fy, fz), side, yaw, leg_len * ratio * _u(rng, 0.92, 1.08)))
    return out


def _wings(sp, rng, seg, wl, ww_frac, folded, spread, p_spread, pairs=1, hind=0.65):
    """Wings hinged on top of the thorax. folded / spread: yaw ranges in degrees from +x."""
    r = rng.random()
    gone = {1, -1} if r < P_WINGS_GONE else ({int(rng.choice([1, -1]))} if r < P_WINGS_GONE + P_WING_ONE else set())
    is_spread = rng.random() < p_spread
    dens = WING_AREAL / (2 * WING_HT)
    for side in (1, -1):
        if side in gone:
            continue
        for k in range(pairs):
            ln = wl * (1.0 if k == 0 else hind) * _u(rng, 0.95, 1.05)
            yaw = _u(rng, *(spread if is_spread else folded)) * D
            elev = (_u(rng, -15, 15) if is_spread else -_u(rng, 0, 8)) * D
            base = sp.pt(seg, 0.2 - 0.3 * k, side * 0.45, 0.7) - [0, 0, 2.5 * WING_HT * k]
            centre = base + 0.47 * ln * _dir(yaw, elev, side)
            R, q = _rot(side * yaw, -elev, rng.normal(0, 5 * D))
            sp.ell(centre, (ln / 2, ln * ww_frac / 2, WING_HT), R, q, dens=dens, rgba=WING_RGBA, body=False)
    state = "wings gone" if len(gone) == 2 else ("one wing side gone, " if gone else "") + (
        "wings spread" if is_spread else "wings folded")
    sp.notes.append(state)


def _antennae(sp, rng, seg, L, parts, r_frac=0.012, fx=0.7, fy=0.35, fz=0.35):
    """parts: [(length / L range, yaw range, elev range)] per antenna segment, base to tip."""
    r = max(LEG_R_MIN, r_frac * L)
    gone = 0
    for side in (1, -1):
        if rng.random() < P_ANTENNA_GONE:
            gone += 1
            continue
        p = sp.pt(seg, fx, side * fy, fz)
        for lr, yr, er in parts:
            q = p + _u(rng, *lr) * L * _dir(_u(rng, *yr) * D, _u(rng, *er) * D, side)
            sp.cap(p, q, r, RHO * min(1.0, (r_frac * L / r) ** 2))
            p = q
    if gone:
        sp.notes.append(f"antennae gone {gone}/2")


# ---- body plans: each fills a _Spec for body length L ----

def _beetle(sp, rng, L):
    wf, tf = _u(rng, 0.7, 1.35), _u(rng, 0.8, 1.15)
    open_ = rng.random() < P_ELYTRA_OPEN
    abd = (0.75, 0.7) if open_ else (1.0, 1.0)
    _segments(sp, rng, L, [("head", 0.14, 0.30, 0.22, -0.03), ("pronotum", 0.24, 0.50, 0.32, 0.0),
                           ("abdomen", 0.62, 0.56 * abd[0], 0.38 * abd[1], 0.02)], wf, tf, rng.normal(0, 3) * D,
              overlap=0.35)
    if open_:   # elytra lifted and spread, hind wings out
        g = sp.seg["abdomen"]
        a, b = g["size"][0], g["size"][1] / abd[0]
        for side in (1, -1):
            yaw, elev = _u(rng, 150, 170) * D, _u(rng, 10, 35) * D
            base = sp.pt("pronotum", -0.8, side * 0.3, 0.5)
            R, q = _rot(side * yaw, -elev, side * _u(rng, -30, 0) * D)
            sp.ell(base + 0.95 * a * _dir(yaw, elev, side), (a, 0.55 * b, max(WING_HT, 0.04 * L)), R, q, body=False)
        _wings(sp, rng, "pronotum", 1.3 * L, 0.3, (60, 110), (60, 110), 1.0)
        sp.notes.insert(0, "elytra open")
    hips = [(sp.pt("pronotum", 0.2, s * 0.35, -0.6), s, 40, 0.9) for s in (1, -1)]
    hips += [(sp.pt("abdomen", fx, s * 0.35, -0.6), s, yaw, ratio)
             for fx, yaw, ratio in ((0.6, 85, 1.0), (0.3, 130, 1.1)) for s in (1, -1)]
    ln = L * _u(rng, 0.5, 0.75)
    hips = [(p, s, y, ln * r * _u(rng, 0.92, 1.08)) for p, s, y, r in hips]
    _legs(sp, rng, hips, 0.035 * L, [0.35, 0.40, 0.25], ((0, 30), (-75, -40)), 0.03)
    _antennae(sp, rng, "head", L, [((0.25, 0.5), (20, 50), (0, 30))], 0.02, fz=0.2)


def _mite(sp, rng, L):
    _segments(sp, rng, L, [("gnathosoma", 0.12, 0.18, 0.12, 0.0), ("body", 0.88, 0.75, 0.5, 0.05)],
              _u(rng, 0.85, 1.15), _u(rng, 0.8, 1.2))
    ln = L * _u(rng, 0.35, 0.6)
    hips = [(sp.pt("body", fx, s * 0.82, -0.3), s, yaw, ln * r * _u(rng, 0.92, 1.08))
            for fx, yaw, r in ((0.55, 35, 1.1), (0.3, 70, 0.9), (0.0, 110, 0.9), (-0.25, 145, 1.0))
            for s in (1, -1)]
    _legs(sp, rng, hips, 0.06 * L, [0.5, 0.3, 0.2], ((0, 25), (-60, -20)), 0.02, "curled")


def _fly(sp, rng, L):
    _segments(sp, rng, L, [("head", 0.17, 0.32, 0.28, 0.03), ("thorax", 0.36, 0.36, 0.36, 0.04),
                           ("abdomen", 0.47, 0.30, 0.24, -0.01)],
              _u(rng, 0.7, 1.15), 1.0, rng.normal(0, 4) * D)
    hips = _insect_hips(sp, rng, "thorax", L * _u(rng, 0.6, 1.0), (0.85, 0.95, 1.15))
    _legs(sp, rng, hips, 0.02 * L, [0.40, 0.35, 0.25], ((5, 35), (-70, -35)), 0.05)
    _wings(sp, rng, "thorax", L * _u(rng, 0.8, 1.05), _u(rng, 0.35, 0.45), (160, 178), (50, 100), 0.35)
    _antennae(sp, rng, "head", L, [((0.08, 0.6), (15, 45), (10, 40))])


def _wasp(sp, rng, L):
    _segments(sp, rng, L, [("head", 0.15, 0.26, 0.20, 0.02), ("thorax", 0.33, 0.24, 0.24, 0.03),
                           ("petiole", 0.06, 0.05, 0.05, 0.0), ("abdomen", 0.46, 0.24, 0.20, -0.01)],
              _u(rng, 0.8, 1.15), 1.0, rng.normal(0, 6) * D)
    hips = _insect_hips(sp, rng, "thorax", L * _u(rng, 0.7, 1.0), (0.85, 0.95, 1.15))
    _legs(sp, rng, hips, 0.02 * L, [0.40, 0.35, 0.25], ((5, 35), (-70, -35)), 0.05)
    _wings(sp, rng, "thorax", L * _u(rng, 0.75, 0.95), 0.32, (165, 178), (55, 100), 0.25, pairs=2)
    _antennae(sp, rng, "head", L, [((0.15, 0.25), (15, 40), (15, 40)), ((0.3, 0.6), (0, 30), (-10, 20))])


def _ant(sp, rng, L):
    _segments(sp, rng, L, [("head", 0.24, 0.22, 0.17, 0.02), ("thorax", 0.30, 0.14, 0.15, 0.02),
                           ("petiole", 0.07, 0.06, 0.10, 0.01), ("abdomen", 0.39, 0.26, 0.22, -0.01)],
              _u(rng, 0.85, 1.15), 1.0, rng.normal(0, 8) * D)
    hips = _insect_hips(sp, rng, "thorax", L * _u(rng, 0.7, 0.95), (0.85, 0.95, 1.1), fy=0.6)
    _legs(sp, rng, hips, 0.02 * L, [0.45, 0.30, 0.25], ((5, 35), (-60, -30)), 0.04)
    _antennae(sp, rng, "head", L, [((0.18, 0.25), (30, 55), (20, 40)), ((0.25, 0.35), (-5, 20), (-25, 5))])  # elbowed


def _mosquito(sp, rng, L):
    _segments(sp, rng, L, [("head", 0.10, 0.13, 0.13, 0.02), ("thorax", 0.25, 0.18, 0.22, 0.04),
                           ("abdomen", 0.65, 0.12, 0.10, 0.0)], _u(rng, 0.85, 1.15), 1.0, rng.normal(0, 5) * D)
    hips = _insect_hips(sp, rng, "thorax", L * _u(rng, 1.3, 2.0), (0.9, 1.0, 1.15), fy=0.55)
    _legs(sp, rng, hips, 0.012 * L, [0.50, 0.25, 0.25], ((-5, 30), (-45, -5)), 0.10, "trailing")
    _wings(sp, rng, "thorax", L * _u(rng, 0.65, 0.8), 0.22, (168, 180), (60, 100), 0.30)
    _antennae(sp, rng, "head", L, [((0.25, 0.4), (10, 30), (5, 30))], 0.008)
    if rng.random() < 0.6:   # proboscis (mosquitoes yes, midges no)
        p = sp.pt("head", 0.8, 0, -0.2)
        sp.cap(p, p + L * _u(rng, 0.35, 0.45) * _dir(0, -_u(rng, 15, 45) * D, 1), max(LEG_R_MIN, 0.01 * L),
               RHO * min(1.0, (0.01 * L / max(LEG_R_MIN, 0.01 * L)) ** 2))


def _cranefly(sp, rng, L):
    _segments(sp, rng, L, [("head", 0.06, 0.08, 0.08, 0.02), ("thorax", 0.20, 0.14, 0.17, 0.03),
                           ("abdomen", 0.74, 0.09, 0.08, 0.0)], _u(rng, 0.85, 1.15), 1.0, rng.normal(0, 4) * D)
    hips = _insect_hips(sp, rng, "thorax", L * _u(rng, 1.7, 2.6), (0.9, 1.0, 1.1), fy=0.55)
    _legs(sp, rng, hips, 0.009 * L, [0.50, 0.20, 0.30], ((-5, 30), (-45, -5)), 0.20, "trailing")
    _wings(sp, rng, "thorax", L * _u(rng, 0.75, 0.9), 0.2, (145, 170), (60, 100), 0.5)
    _antennae(sp, rng, "head", L, [((0.15, 0.3), (10, 35), (5, 30))], 0.006)


def _spider(sp, rng, L):
    _segments(sp, rng, L, [("head", 0.42, 0.36, 0.24, 0.03), ("abdomen", 0.58, 0.46, 0.42, 0.02)],
              _u(rng, 0.8, 1.2), _u(rng, 0.85, 1.15))
    ln = L * _u(rng, 0.8, 1.8)
    hips = [(sp.pt("head", fx, s * 0.75, -0.2), s, yaw, ln * r * _u(rng, 0.92, 1.08))
            for fx, yaw, r in ((0.5, 30, 1.0), (0.2, 65, 0.9), (-0.15, 105, 0.75), (-0.45, 145, 0.95))
            for s in (1, -1)]
    _legs(sp, rng, hips, 0.03 * L, [0.30, 0.45, 0.25], ((10, 40), (-60, -25)), 0.06, "curled")
    _antennae(sp, rng, "head", L, [((0.08, 0.12), (10, 30), (-20, 10)), ((0.06, 0.1), (-10, 10), (-60, -30))],
              0.025, fx=0.85, fy=0.3, fz=-0.2)   # pedipalps


BUILDERS = {"beetle": _beetle, "mite": _mite, "fly": _fly, "wasp": _wasp, "ant": _ant,
            "mosquito": _mosquito, "cranefly": _cranefly, "spider": _spider}


def _extent(g):
    """Axis-aligned half extents and centre of a geom, plus its farthest distance from the origin."""
    if g["type"] == "capsule":
        lo, hi = np.minimum(g["a"], g["b"]) - g["r"], np.maximum(g["a"], g["b"]) + g["r"]
        return lo, hi, max(np.linalg.norm(g["a"]), np.linalg.norm(g["b"])) + g["r"]
    h = np.sqrt(((g["R"] * g["size"]) ** 2).sum(axis=1))
    return g["pos"] - h, g["pos"] + h, np.linalg.norm(g["pos"]) + g["size"].max()


def _f(v):
    return " ".join(f"{x:.5g}" for x in v)


def _finish(sp, kind, plan, L):
    body = [_extent(g) for g in sp.geoms if g["body"]]
    lo, hi = np.min([b[0] for b in body], axis=0), np.max([b[1] for b in body], axis=0)
    shift = (lo + hi) / 2
    for g in sp.geoms:
        for k in ("pos", "a", "b"):
            if k in g:
                g[k] = g[k] - shift
    length, width, thickness = sorted(hi - lo, reverse=True)
    span = 2 * max(_extent(g)[2] for g in sp.geoms)
    lines = [f"<!-- {plan} L={L:.2f}mm, {', '.join(sp.notes)} -->"]
    for g in sp.geoms:
        common_attr = f'density="{g["dens"]:.4g}" rgba="{_f(g["rgba"])}"'
        if g["type"] == "capsule":
            lines.append(f'<geom type="capsule" fromto="{_f(g["a"])} {_f(g["b"])}" size="{g["r"]:.4g}" {common_attr}/>')
        else:
            lines.append(f'<geom type="ellipsoid" size="{_f(g["size"])}" pos="{_f(g["pos"])}" '
                         f'quat="{_f(g["quat"])}" {common_attr}/>')
    dims = {"length": round(float(length), 4), "width": round(float(width), 4),
            "thickness": round(float(thickness), 4), "span": round(float(span), 4)}
    return common.Particle(kind=kind, group="insect", xml="\n".join(lines), dims=dims)


def _length(rng, median, sigma, lo, hi):
    for _ in range(100):
        L = median * np.exp(sigma * rng.standard_normal())
        if lo <= L <= hi:
            return L
    return float(np.clip(median, lo, hi))


def make(kind: str, rng: np.random.Generator, size_scale: float = 1.0, plan: str | None = None) -> common.Particle:
    """One preserved specimen of the given kind. plan forces a body plan (e.g. "spider") for galleries."""
    if kind in MALAISE_KINDS:
        return _make_malaise(kind, rng, size_scale, plan)
    plans = PLANS[kind]
    names = list(plans)
    w = np.array([plans[n][0] for n in names])
    plan = plan or names[rng.choice(len(names), p=w / w.sum())]
    _, median, sigma, lo, hi = plans[plan]
    L = _length(rng, median, sigma, lo, hi) * size_scale
    shade = _u(rng, 0.85, 1.15)
    sp = _Spec(tuple(min(1.0, c * shade) for c in COLORS[kind]))
    BUILDERS[plan](sp, rng, L)
    return _finish(sp, kind, plan, L)


# ---------- the real Malaise mix (sim/INSECT_AUDIT.md, proposal 1) ----------
# KINDS and PLANS above stay frozen (sim/opt/leaderboard_insects.md depends on them). These kinds are new.
# Body length L is drawn from ONE lognormal fitted to EntoSieve's two counted Malaise samples (Ascenzi et al. 2025,
# PMC12225705: 10,276 and 12,482 specimens in < 1.5 / 1.5-3 / 3-5 / > 5 mm bins). MALAISE_FIT is the physics
# session's maximum-likelihood fit to the pooled counts, truncated to [0.3, 20] mm: it gives 0.570 / 0.291 / 0.099 /
# 0.041 in those bins against the data's 0.570 / 0.290 / 0.100 / 0.041 (per sample: median 1.27 sigma 0.86, and
# 1.28 sigma 0.70). The first bin is 0-1.5 mm, so the tail under 1 mm is extrapolated, and the 0.3 mm floor is
# ASSUMED. Then the body plan is drawn given L:
#     P(plan | L) ~ weight * lognormal_pdf(L; median, sigma) on [lo, hi]
# so the size mix is the data's and the plans only decide shape. Plan weights put Diptera near 72% (BIOSCAN-5M's
# order counts) and cut mites and spiders, which Malaise traps rarely catch; the per-plan sizes are textbook small
# Malaise taxa (gall midges, phorids, sciarids, micro-Hymenoptera). Both are ASSUMED, not fitted.
# Below about 0.8 mm the legs sit at LEG_R_MIN, so they are fatter than real (as for mites already).
MALAISE_FIT = (1.274, 0.779, 0.3, 20.0)    # median L mm, sigma, min, max
# plan: (weight, median L mm, sigma, min L, max L)
MALAISE_PLANS = {
    "fly": (0.50, 1.4, 0.60, 0.4, 15.0),        # gall midges, phorids, sciarids, small flies
    "mosquito": (0.18, 2.0, 0.50, 0.6, 9.0),    # chironomids, ceratopogonids, mosquitoes
    "cranefly": (0.04, 8.0, 0.35, 4.0, 20.0),
    "wasp": (0.14, 1.2, 0.65, 0.3, 18.0),       # parasitoids and micro-Hymenoptera
    "ant": (0.02, 3.5, 0.40, 1.5, 15.0),
    "beetle": (0.06, 2.0, 0.60, 0.8, 15.0),
    "spider": (0.03, 2.0, 0.50, 0.8, 12.0),
    "mite": (0.03, 0.6, 0.35, 0.3, 2.0),
}
# kind: the L range it draws from. insect_malaise has the real shares; the three class kinds draw L from the same fit
# cut to one BugPicker class, for stratified runs (oversample the rare > 6 mm, then weight scores by MALAISE_SHARES).
MALAISE_KINDS = {"insect_malaise": (0.3, 20.0),
                 "insect_malaise_lt2": (0.3, 2.0),
                 "insect_malaise_2to6": (2.0, 6.0),
                 "insect_malaise_gt6": (6.0, 20.0)}
# Real BugPicker class shares under MALAISE_FIT (numerical, 0.3-20 mm): weight stratified results by these.
MALAISE_SHARES = {"< 2 mm": 0.710, "2-6 mm": 0.266, "> 6 mm": 0.024}
# Mix presets for --mix / --clump / optimize.py STUDIES. 60 specimens is about the insect study's 65 in cost.
MALAISE_MIX = {"insect_malaise": 60}
MALAISE_MIX_STRATIFIED = {"insect_malaise_lt2": 24, "insect_malaise_2to6": 24, "insect_malaise_gt6": 12}
PLAN_COLOR = {plan: COLORS[kind] for kind, plans in PLANS.items() for plan in plans}


def _lognormal_pdf(L, median, sigma):
    return np.exp(-0.5 * (np.log(L / median) / sigma) ** 2) / (L * sigma)


def malaise_length(rng, lo=MALAISE_FIT[2], hi=MALAISE_FIT[3]):
    """Body length (mm) from the EntoSieve fit, truncated to [lo, hi] (rejection in blocks: > 6 mm accepts ~2.4%)."""
    median, sigma = MALAISE_FIT[:2]
    while True:
        L = median * np.exp(sigma * rng.standard_normal(1024))
        L = L[(L >= lo) & (L <= hi)]
        if len(L):
            return float(L[0])


def malaise_plan(L, rng):
    """A body plan for a specimen of length L: P(plan | L) ~ weight * that plan's lognormal at L, inside its range."""
    names = list(MALAISE_PLANS)
    p = np.array([w * _lognormal_pdf(L, m, s) if lo <= L <= hi else 0.0
                  for w, m, s, lo, hi in (MALAISE_PLANS[n] for n in names)])
    return names[rng.choice(len(names), p=p / p.sum())] if p.sum() > 0 else "fly"


def _make_malaise(kind, rng, size_scale=1.0, plan=None):
    if plan:
        _, median, sigma, lo, hi = MALAISE_PLANS[plan]
        L = _length(rng, median, sigma, lo, hi)
    else:
        L = malaise_length(rng, *MALAISE_KINDS[kind])
        plan = malaise_plan(L, rng)
    L *= size_scale
    shade = _u(rng, 0.85, 1.15)
    sp = _Spec(tuple(min(1.0, c * shade) for c in PLAN_COLOR[plan]))
    BUILDERS[plan](sp, rng, L)
    return _finish(sp, kind, plan, L)


def _malaise_summary(n=3000):
    """Print each Malaise kind's class shares, plan shares and geoms (python insects.py malaise)."""
    rng = np.random.default_rng(0)
    for kind in MALAISE_KINDS:
        rows = []
        for _ in range(n if kind == "insect_malaise" else n // 3):
            p = make(kind, rng)
            plan, L = p.xml.split()[1], float(p.xml.split()[2][2:-3])
            rows.append((plan, L, p.dims["length"], p.xml.count("<geom")))
        L = np.array([r[1] for r in rows])
        geoms = np.array([r[3] for r in rows])
        plans = {pl: np.mean([r[0] == pl for r in rows]) for pl in MALAISE_PLANS}
        print(f"{kind}: n {len(rows)}, L median {np.median(L):.2f} mm, < 1.5 mm {np.mean(L < 1.5):.3f}, "
              f"< 2 / 2-6 / > 6 mm {np.mean(L < 2):.3f} / {np.mean((L >= 2) & (L <= 6)):.3f} / {np.mean(L > 6):.3f}, "
              f"> 5 mm {np.mean(L > 5):.3f}, geoms {geoms.min()}-{geoms.max()} (mean {geoms.mean():.1f})")
        print("    plans: " + ", ".join(f"{pl} {s:.3f}" for pl, s in plans.items() if s > 0)
              + f"; Diptera {sum(plans[pl] for pl in ('fly', 'mosquito', 'cranefly')):.3f}")


if __name__ == "__main__":
    import sys
    if "malaise" in sys.argv[1:]:
        _malaise_summary()
        sys.exit()
    rng = np.random.default_rng(0)
    print(f"{'kind':16s} {'plan':9s} {'share':>5s} {'L med':>6s} {'L p90':>6s} {'<5mm':>5s} "
          f"{'w med':>6s} {'span/L':>7s} {'span max':>8s} {'geoms':>6s}")
    for kind in KINDS:
        rows = {}
        for _ in range(2000):
            p = make(kind, rng)
            plan, L = p.xml.split()[1], float(p.xml.split()[2][2:-3])
            rows.setdefault(plan, []).append((L, p.dims["width"], p.dims["span"] / L, p.dims["span"],
                                              p.xml.count("<geom")))
        allL = np.concatenate([np.array(r)[:, 0] for r in rows.values()])
        for plan, r in rows.items():
            a = np.array(r)
            print(f"{kind:16s} {plan:9s} {len(a) / 2000:5.2f} {np.median(a[:, 0]):6.2f} {np.percentile(a[:, 0], 90):6.2f} "
                  f"{np.mean(a[:, 0] < 5):5.2f} {np.median(a[:, 1]):6.2f} {np.median(a[:, 2]):7.2f} "
                  f"{a[:, 3].max():8.1f} {a[:, 4].min():3.0f}-{a[:, 4].max():.0f}")
        print(f"{kind:16s} {'all':9s} {'':5s} {np.median(allL):6.2f} {np.percentile(allL, 90):6.2f} {np.mean(allL < 5):5.2f}")
