"""Clumps and debris for the sorter sim (docs/SYSTEM.md section 1, docs/sessions/clump-breakup.md part A). Units mm, g, s.

A Malaise sample arrives as a compacted ball of tangled insects mixed with leaves, twigs and dirt. Breaking it
apart gently is the system's real job; size sorting comes after. This module adds that input to sorter.py.

The clump (Clumps):
  - N specimens (insects.py kinds, or grains.py surrogates for the bench demo) plus debris, packed into a ball by a
    short pre-sim of the clump alone: no gravity, every body pulled toward the clump's centre of mass at PULL_G
    with its speed damped, then the pull switched off and the pile relaxed while its contacts stiffen to the run's
    own, so no contact is left loaded (grains: no overlap left; interlocked insect legs keep about 0.1 mm). Leaves
    join after the core has packed: each is laid against the ball's surface (mostly the upper half) and pressed
    on, so it sticks to the outside instead of splitting the ball in two.
  - Every pair of bodies whose geoms come within gap_mm of each other is joined by a breakable bond: a MuJoCo
    equality, "connect" by default (a ball joint at the contact point: it carries force, not torque, like
    tangled legs or a liquid bridge), or "weld" (also locks the relative orientation). Bonds are made at the
    packed pose, which becomes the model's qpos0, so they start satisfied and unloaded.
  - Bonds can't break during the settle: it sets the clump down (at up to the settle's 100 mm/s), it doesn't drop
    it, and a landing on stiff contacts would shatter a brittle ball. Breaking starts with the shake.
  - Every step the bond's load is read from its constraint rows in d.efc_force (the norm of the 3 position
    rows; a weld also counts its 3 rotation rows over the bond's radius), and d.eq_active is switched off for
    good once the load exceeds
        bond_N(w) = sigma * r_pair * (1 - k_wet * w)
    where r_pair = 2 r1 r2 / (r1 + r2) is the harmonic mean of the two bodies' half widths (a capillary bridge
    pulls with 2 pi gamma R, so strength per mm of radius is the natural unit), w is the mean wetness of the two
    bodies from spray.py (0 with no spray), and sigma (uN per mm) comes from the bond set:
        weak     5000   5 mN between two rice grains (r_pair 1 mm), 30 x a grain's weight
        medium  10000   10 mN, 60 x
        strong  25000   25 mN, 150 x
    ASSUMED: nobody has measured what holds a Malaise clump together, so the sets are placed on the loads the
    clump itself sees, measured with unbreakable bonds on the demo clump (50 rice + 50 quinoa + 6 pasta +
    debris) in inserts:5mm,2mm,pitch=85 (CLUMPS.md). Lying still on the 5 mm tray, a bond's load over r_pair
    peaks at 4530 uN/mm (p99 2130); over one +/-10 deg, 2 s seesaw cycle at p90 4680, p99 10060, max 25700.
    So weak just holds itself up at rest (any weaker and the clump falls apart under its own weight as soon
    as it is set down), medium is the cycle's p99 and strong its maximum. Rank designs across all three,
    like the friction sets. k_wet (0.6) is ASSUMED too: wetting weakens bonds (SYSTEM.md section 4); fully
    wet, strong drops to medium and medium to below what holds the clump up.
  - Bonded pairs keep their contacts, so the clump's geoms still collide with each other; a freed specimen is
    an ordinary particle.

Debris kinds (make_debris; also usable loose in --mix):
    leaf   a thin rigid plate (box) 12-30 mm long, 0.5-0.9 as wide, 0.2 mm thick, wet-leaf density 0.8e-3.
           RIGID: real leaf bits bend and wrap. The 0.2 mm is real and also the stability floor here.
    twig   a capsule 1-3 mm across, 10-30 mm long, wet wood 0.75e-3
    dirt   a sphere 0.5-1 mm across, 2.6e-3 (mineral soil). Real soil goes down to 0.1 mm; grains below 0.5 mm
           are left out because they need a smaller timestep and pass every screen anyway.

Metrics (Clumps.metrics, in results["clumps"]):
  - break-up: the fraction of the clump's specimens that are free (no live bond) over time, t50 and t90 (s from
    the start of the shake; null if never reached), and the largest cluster of specimens still bonded together
    at the end. Debris counts as glue in a cluster, but only specimens are counted.
  - damage proxy: the peak contact normal force on each specimen body over the shake (pyramidal cone: the sum
    of a contact's edge forces), its p50 / p90 / max, and the share of specimens over fragile_mN (default
    FRAGILE_MN, ASSUMED; a parameter); and the same counted only while the specimen is still bonded ("bonded_*":
    what the break-up itself does to it, as against the drops between levels once it is free). The contact
    stiffness sets these peaks (a landing gives about m v / timeconst), so they rank designs and strokes; they
    are not newtons to quote until calibrated.
  - leaf blinding: the share of each printed screen's holes that lie under a leaf lying flat on it (within
    BLIND_DZ of the surface, tilted under BLIND_TILT_DEG), at the end and over time.
  - sort: for the clump's specimens, the share that ended in their ideal zone, by kind (the run's usual counts
    and recovery cover every particle).

Use from sorter.py (--clump), e.g. a bench-demo clump of grain surrogates on the seesaw tower:
    <venv python> sorter.py --design inserts:5mm,2mm,pitch=85 --mix "" \\
        --clump rice=50,quinoa=50,pasta=6,leaf=1,twig=2,dirt=10,bond=medium \\
        --stroke seesaw:deg=10,period_s=2 --duration 6 --dt 0.000125 --timeconst 0.00025 --fps 30 --out out/runs/clump
    (insect_malaise clumps need --dt 0.0000625: at 0.125 ms they go unstable in the settle; CLUMPS.md)
Options in --clump (with the kinds): bond (weak / medium / strong, or sigma in uN/mm), k_wet, type (connect /
weld), gap_mm, timeconst (bond solref, s), fragile_mN, pull_g, seed, solver (cg / newton / pgs).

Solver (option solver): the packing pre-sim uses CG for grains, which is 6x faster there (3.6 ms against 20 per step
for 106 grains: Newton's sparse Cholesky fills in on a bonded ball) and only has to leave a tidy pile; insects pack
with Newton, because CG blew up on their interlocked legs within 0.03 s. The run itself keeps
Newton. On the seesaw tower, whose driven trays weigh 1e6 g against milligram grains, CG and PGS hit their
iteration cap and their constraint forces disagree with Newton's (bond-load p90 5.7 mN with CG, 0.9 with PGS, 1.4
with Newton in the same 0.3 s), and those forces are exactly what breaks bonds. Newton costs about 12 ms per step
for a 120-body clump, so a 10 s seesaw run takes about 20 min on one core.

Run from sim\\ to pack one clump and print it:  <venv python> clumps.py rice=50,quinoa=50,pasta=6,leaf=1
"""
import sys

import mujoco
import numpy as np

import common

DEBRIS = ("leaf", "twig", "dirt")
BOND_SETS = {"weak": 5000.0, "medium": 10000.0, "strong": 25000.0}  # sigma, uN per mm of r_pair (ASSUMED)
DEFAULTS = {"bond": "medium", "k_wet": 0.6, "type": "connect", "gap_mm": 0.3, "timeconst": 0.002,
            "fragile_mN": 5.0, "pull_g": 3.0, "seed": None, "solver": "newton"}
SOLVERS = {"newton": mujoco.mjtSolver.mjSOL_NEWTON, "cg": mujoco.mjtSolver.mjSOL_CG, "pgs": mujoco.mjtSolver.mjSOL_PGS}
FRAGILE_MN = DEFAULTS["fragile_mN"]
G = 9810.0
PACK_DT = 2e-4             # s, packing pre-sim timestep
PACK_S, LEAF_S, RELAX_S = 0.4, 0.15, 0.12    # s: core packing, leaves pressed on, relax with the pull off
PACK_DAMP, RELAX_DAMP = 30.0, 300.0          # 1/s, speed damping while packing and relaxing
RELAX_STAGES = 4           # the relax stiffens contacts from 2 ms to the run's time constant in this many steps
PACK_R0 = 2.0              # mm: the pull fades linearly inside this distance of the centre
BOND_SOLIMP = "0.9 0.95 0.001"
BLIND_DZ = 2.0             # mm: a leaf this close to a screen's top surface lies on it
BLIND_TILT_DEG = 30.0      # and is tilted less than this from the screen's plane
EQ_ROW = int(mujoco.mjtConstraint.mjCNSTR_EQUALITY)

LEAF = {"length": (12.0, 30.0), "aspect": (0.5, 0.9), "thick": 0.2, "density": 0.8e-3, "rgba": "0.42 0.55 0.18 1"}
TWIG = {"d": (1.0, 3.0), "length": (10.0, 30.0), "density": 0.75e-3, "rgba": "0.45 0.31 0.17 1"}
DIRT = {"d": (0.5, 1.0), "density": 2.6e-3, "rgba": "0.30 0.24 0.18 1"}


# ---------- debris ----------
def make_debris(kind, rng):
    """One piece of debris as a common.Particle (group "debris")."""
    if kind == "leaf":
        L = rng.uniform(*LEAF["length"])
        W, t = L * rng.uniform(*LEAF["aspect"]), LEAF["thick"]
        xml = (f'<geom type="box" size="{L / 2:.4f} {W / 2:.4f} {t / 2:.4f}" density="{LEAF["density"]:g}" '
               f'rgba="{LEAF["rgba"]}"/>')
        dims = {"length": L, "width": W, "thickness": t, "span": float(np.hypot(L, W))}
    elif kind == "twig":
        d, L = rng.uniform(*TWIG["d"]), rng.uniform(*TWIG["length"])
        xml = (f'<geom type="capsule" size="{d / 2:.4f} {L / 2:.4f}" density="{TWIG["density"]:g}" '
               f'rgba="{TWIG["rgba"]}"/>')
        dims = {"length": L + d, "width": d, "thickness": d, "span": L + d}
    elif kind == "dirt":
        d = rng.uniform(*DIRT["d"])
        xml = f'<geom type="sphere" size="{d / 2:.4f}" density="{DIRT["density"]:g}" rgba="{DIRT["rgba"]}"/>'
        dims = {"length": d, "width": d, "thickness": d, "span": d}
    else:
        raise ValueError(f"unknown debris {kind!r}: use one of {DEBRIS}")
    return common.Particle(kind, "debris", xml, {k: float(v) for k, v in dims.items()})


# ---------- spec ----------
def parse(s):
    """'rice=40,quinoa=40,leaf=1,bond=weak' -> {"kinds": {...}, options...}, as RunConfig.clump."""
    import sorter
    kv = sorter.parse_kv(s) if isinstance(s, str) else dict(s)
    return {"kinds": {k: int(v) for k, v in kv.items() if k not in DEFAULTS},
            **{k: v for k, v in kv.items() if k in DEFAULTS}}


def bond_sigma(bond):
    if isinstance(bond, (int, float)):
        return float(bond)
    if bond not in BOND_SETS:
        raise ValueError(f"unknown bond set {bond!r}: use one of {list(BOND_SETS)} or sigma in uN/mm")
    return BOND_SETS[bond]


def half_width(p):
    """Half width of a particle's body (mm), the radius a bond's strength scales with."""
    return 0.5 * min(p.dims["width"], p.dims["length"])


# ---------- packing ----------
def _quat_z_to(u, spin):
    """wxyz quaternion turning +z onto unit u, then spinning by `spin` about u."""
    z = np.array([0.0, 0.0, 1.0])
    axis, c = np.cross(z, u), float(np.dot(z, u))
    s = np.linalg.norm(axis)
    q1 = np.array([1.0, 0, 0, 0]) if s < 1e-9 else np.concatenate([[np.cos(np.arctan2(s, c) / 2)],
                                                                      np.sin(np.arctan2(s, c) / 2) * axis / s])
    q2 = np.concatenate([[np.cos(spin / 2)], np.sin(spin / 2) * u])
    out = np.zeros(4)
    mujoco.mju_mulQuat(out, q2, q1)
    return out


def pack(parts, rng, friction=0.4, pull_g=3.0, gap=0.3, timeconst=0.002, dt=PACK_DT):
    """Pack parts into a ball (see the module docstring). Returns positions relative to the ball's centre of
    mass (n x 3), body quaternions (n x 4), the radius that bounds every geom (mm), the specimens' radius (95th
    percentile of their geom centres' distance from the centre, plus a median half width), the bonded pairs
    [(i, j, contact point relative to the centre)] and the largest overlap left (mm). timeconst, dt: the run's
    contact time constant and timestep, used for the relax."""
    import sorter
    n = len(parts)
    if any("<body" in p.xml for p in parts):
        raise ValueError("clump particles must be single rigid bodies")
    leaf = np.array([p.kind == "leaf" for p in parts])
    core = [p for p, lf in zip(parts, leaf) if not lf]
    r = np.array([min(p.dims["span"] / 2, p.dims["length"]) * 1.05 for p in core])
    side = max((np.sum((2 * r) ** 3) / 0.3) ** (1 / 3), 2.2 * r.max())
    for _ in range(20):
        try:
            start = sorter.place(core, [-side / 2, side / 2] * 3, rng)
            break
        except RuntimeError:
            side *= 1.25
    pos, k = [], 0
    for i in range(n):
        if leaf[i]:
            pos.append(np.array([0.0, 0.0, 1e4 + 200.0 * i]))       # parked far away until the core has packed
        else:
            pos.append(start[k])
            k += 1
    bodies = []
    for i, (p, xyz) in enumerate(zip(parts, pos)):
        q = rng.normal(size=4)
        q /= np.linalg.norm(q)
        bodies.append(f'<body name="c{i}" pos="{xyz[0]:.4f} {xyz[1]:.4f} {xyz[2]:.4f}" '
                      f'quat="{q[0]:.5f} {q[1]:.5f} {q[2]:.5f} {q[3]:.5f}"><freejoint/>{p.xml.replace("{p}", f"c{i}")}</body>')
    solver = "Newton" if any(p.group == "insect" for p in parts) else "CG"    # CG blows up on interlocked legs
    m = mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="{PACK_DT}" gravity="0 0 0" integrator="implicitfast" solver="{solver}"/>
  <size memory="64M"/><default><geom solref="0.002 1" solimp="{sorter.SOLIMP}" friction="{friction} 0.005 0.0001"/></default>
  <worldbody>{"".join(bodies)}</worldbody></mujoco>""")
    d = mujoco.MjData(m)
    ids = np.array([m.body(f"c{i}").id for i in range(n)])
    qadr = m.jnt_qposadr[m.body_jntadr[ids]]
    mass = m.body_mass[ids]

    def run(seconds, active, damp):
        keep = np.exp(-damp * m.opt.timestep)
        for _ in range(round(seconds / m.opt.timestep)):
            d.xfrc_applied[:] = 0.0
            if active.any():
                x = d.xipos[ids]
                c = (mass[active, None] * x[active]).sum(0) / mass[active].sum()
                v = x - c
                dist = np.maximum(np.linalg.norm(v, axis=1, keepdims=True), PACK_R0)
                d.xfrc_applied[ids, :3] = -(pull_g * G * mass * active)[:, None] * v / dist
            mujoco.mj_step(m, d)
            d.qvel *= keep

    run(PACK_S, ~leaf, PACK_DAMP)
    if leaf.any():
        mujoco.mj_forward(m, d)
        x = d.xipos[ids][~leaf]
        c = (mass[~leaf, None] * x).sum(0) / mass[~leaf].sum()
        R = max(np.linalg.norm(d.geom_xpos[g] - c) + m.geom_rbound[g]
                for g in range(m.ngeom) if not leaf[np.searchsorted(ids, m.geom_bodyid[g])])
        for i in np.flatnonzero(leaf):
            u = rng.normal(size=3)
            u[2] = abs(u[2]) + 0.5                       # mostly on the upper half
            u /= np.linalg.norm(u)
            d.qpos[qadr[i]:qadr[i] + 3] = c + u * (R + 1.0)
            d.qpos[qadr[i] + 3:qadr[i] + 7] = _quat_z_to(u, rng.uniform(0, 2 * np.pi))
        d.qvel[:] = 0.0
        run(LEAF_S, np.ones(n, bool), PACK_DAMP)
    # Relax with the pull off, stiffening the contacts step by step to the run's own, so the run starts with no
    # contact loaded. Going straight to stiff contacts blows up interlocked insect legs.
    m.opt.timestep = min(PACK_DT, dt)
    for tc in np.geomspace(0.002, min(timeconst, 0.002), RELAX_STAGES):
        m.geom_solref[:, 0] = max(tc, 2 * m.opt.timestep)
        run(RELAX_S / RELAX_STAGES, np.zeros(n, bool), RELAX_DAMP)
    d.qvel[:] = 0.0
    mujoco.mj_forward(m, d)
    overlap = float(max(0.0, -min((d.contact[k].dist for k in range(d.ncon)), default=0.0)))
    if not np.all(np.isfinite(d.qpos)) or np.abs(d.xpos[ids]).max() > 50 * side:
        raise RuntimeError(f"clump packing blew up ({len(parts)} bodies); try a softer run timeconst or a smaller pull_g")
    c = (mass[:, None] * d.xipos[ids]).sum(0) / mass.sum()
    reach = np.linalg.norm(d.geom_xpos - c, axis=1) + m.geom_rbound
    spec = np.array([parts[np.searchsorted(ids, b)].group != "debris" for b in m.geom_bodyid])
    radius = float(reach.max())
    hw = np.median([half_width(p) for p in parts if p.group != "debris"]) if spec.any() else 0.0
    core_r = float(np.percentile(np.linalg.norm(d.geom_xpos[spec] - c, axis=1), 95) + hw) if spec.any() else radius
    rel, quat = d.xpos[ids] - c, d.xquat[ids].copy()

    m.geom_margin[:] = gap                               # every pair within gap of touching becomes a bond
    mujoco.mj_forward(m, d)
    index = {int(b): i for i, b in enumerate(ids)}
    best = {}
    for k in range(d.ncon):
        con = d.contact[k]
        a, b = sorted((index[int(m.geom_bodyid[con.geom[0]])], index[int(m.geom_bodyid[con.geom[1]])]))
        if a != b and con.dist < gap and ((a, b) not in best or con.dist < best[(a, b)][0]):
            best[(a, b)] = (con.dist, con.pos - c)
    pairs = [(a, b, p) for (a, b), (_, p) in sorted(best.items())]
    return rel, quat, radius, core_r, pairs, overlap


def _rot(q):
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, q)
    return R.reshape(3, 3)


# ---------- screens, for leaf blinding ----------
def screen_holes(design):
    """[(zone, top surface z, hole centres (n x 2, tray frame))] for each layer of the design with known holes:
    a layer's own "hole_centres_mm" if it has them, else the printed square-hole inserts (designs_holder.py)."""
    out = []
    for L in design.info.get("layers", []):
        if "hole_centres_mm" in L:
            xy = np.array(L["hole_centres_mm"], float)
        elif str(L.get("insert", "")).startswith("sieve_insert_"):
            import designs_holder
            si = designs_holder.cad()[1]
            hole, bar, _t = si.INSERTS[L["insert"]]
            pitch = hole + bar
            xy = []
            for cx, cy, wl, ww in si.windows():
                nx, ny = int((wl - bar) // pitch), int((ww - bar) // pitch)
                xs = cx + (np.arange(nx) - (nx - 1) / 2) * pitch
                ys = cy + (np.arange(ny) - (ny - 1) / 2) * pitch
                xy += [(x, y) for x in xs for y in ys]
            xy = np.array(xy)
        else:
            continue
        out.append((L["zone"], float(L["surface_z_mm"][1]), xy))
    return out


class Clumps:
    """One clump in a run: its particles, packing, bonds, the per-step bond breaking and the metrics."""

    @classmethod
    def of(cls, cfg, rng):
        """A Clumps for a RunConfig with a clump spec, else None."""
        spec = getattr(cfg, "clump", None)
        if not spec:
            return None
        return cls(parse(spec) if isinstance(spec, str) else spec, rng, cfg.contact["friction"],
                   cfg.contact["timeconst"], cfg.dt)

    def __init__(self, spec, rng, friction=0.4, timeconst=0.002, dt=PACK_DT):
        import sorter
        unknown = set(spec) - set(DEFAULTS) - {"kinds"}
        if unknown:
            raise ValueError(f"unknown clump option(s) {sorted(unknown)}: use {sorted(DEFAULTS)} and particle kinds")
        self.opt = {**DEFAULTS, **{k: v for k, v in spec.items() if k != "kinds"}}
        self.spec = {"kinds": dict(spec.get("kinds", {})), **self.opt}
        if self.opt["type"] not in ("connect", "weld"):
            raise ValueError(f"bond type {self.opt['type']!r}: use connect or weld")
        if self.opt["seed"] is not None:
            rng = np.random.default_rng(int(self.opt["seed"]))
        self.sigma = bond_sigma(self.opt["bond"])
        self.particles = [sorter.make_particle(k, rng) for k, n in self.spec["kinds"].items() for _ in range(n)]
        if not self.particles:
            raise ValueError("an empty clump: give it kinds, e.g. rice=40,quinoa=40")
        self.kinds = list(dict.fromkeys(p.kind for p in self.particles))
        self.rel, self.quats, self.radius, self.core_r, self.pairs, self.overlap = pack(
            self.particles, rng, friction, self.opt["pull_g"], self.opt["gap_mm"], timeconst, dt)
        hw = np.array([half_width(p) for p in self.particles])
        a, b = (np.array([pr[k] for pr in self.pairs], int) for k in (0, 1))
        self.a, self.b = a, b
        self.r_pair = 2 * hw[a] * hw[b] / (hw[a] + hw[b])
        self.f_dry = self.sigma * self.r_pair                       # uN (g mm / s^2)
        self.is_spec = np.array([p.group != "debris" for p in self.particles])
        self.offset = None

    # ---------- model (sorter.build_model) ----------
    def place(self, particles, spawn, rng):
        """Positions for all of a run's particles: the loose ones (first) by sorter.place above the clump, the
        clump (last) as packed, its lowest point just above the spawn box's floor."""
        import sorter
        self.offset = len(particles) - len(self.particles)
        x0, x1, y0, y1, z0, z1 = spawn
        z_low = float(np.min(self.rel[:, 2])) - self.radius
        self.centre = np.array([(x0 + x1) / 2, (y0 + y1) / 2, z0 + 0.5 + max(self.radius, -z_low)])
        pos = list(self.centre + self.rel)
        if self.offset:
            top = self.centre[2] + self.radius + 1.0
            pos = sorter.place(particles[:self.offset], [x0, x1, y0, y1, top, top + max(z1 - z0, 30.0)], rng) + pos
        return pos

    def quat(self, i, q):
        """Particle i's starting orientation: as packed for the clump's own particles, else q."""
        return self.quats[i - self.offset] if i >= self.offset else q

    def names(self):
        return [f"p{self.offset + k:03d}" for k in range(len(self.particles))]   # sorter.run's naming

    def equality_xml(self):
        """The bonds as <equality> elements, satisfied at the packed pose (qpos0)."""
        nm, out = self.names(), []
        sol = f'solref="{self.opt["timeconst"]:g} 1" solimp="{BOND_SOLIMP}"'
        for k, (i, j, p) in enumerate(self.pairs):
            if self.opt["type"] == "connect":    # anchor in body1's frame
                an = _rot(self.quats[i]).T @ (p - self.rel[i])
                out.append(f'<connect name="bond{k}" body1="{nm[i]}" body2="{nm[j]}" '
                           f'anchor="{an[0]:.5f} {an[1]:.5f} {an[2]:.5f}" {sol}/>')
            else:                                # weld: anchor in body2's frame
                an = _rot(self.quats[j]).T @ (p - self.rel[j])
                out.append(f'<weld name="bond{k}" body1="{nm[i]}" body2="{nm[j]}" '
                           f'anchor="{an[0]:.5f} {an[1]:.5f} {an[2]:.5f}" {sol}/>')
        return "<equality>" + "".join(out) + "</equality>" if out else ""

    # ---------- run (sorter.run) ----------
    def bind(self, m, d, design, rock=None, sp=None, every=1, n_settle=0):
        m.opt.solver = SOLVERS[self.opt["solver"]]
        self.eq = np.array([m.equality(f"bond{k}").id for k in range(len(self.pairs))], int)
        self.eq_bond = np.full(m.neq, -1)
        self.eq_bond[self.eq] = np.arange(len(self.eq))
        self.body = np.array([m.body(n).id for n in self.names()])
        self.ba, self.bb = self.body[self.a], self.body[self.b]
        self.sp, self.rock, self.design = sp, rock, design
        self.every, self.n_settle, self.dt = every, n_settle, m.opt.timestep
        self.live = np.ones(len(self.eq), bool)
        self.t_break = np.full(len(self.eq), np.nan)
        self.load_at_break = np.full(len(self.eq), np.nan)
        self.peak_load = np.zeros(len(self.eq))
        self.peak = np.zeros(m.nbody)                 # peak contact normal force per body, uN, during the shake
        self.peak_bonded = np.zeros(m.nbody)          # ... while the body still has a live bond (the break-up)
        self.peak_settle = np.zeros(m.nbody)
        self.bonded = np.zeros(m.nbody, bool)
        self.bonded[self.body[~self.free_mask()]] = True
        self.leaves = [(int(b), m.geom_size[np.flatnonzero(m.geom_bodyid == b)[0]][:2].copy())
                       for b, p in zip(self.body, self.particles) if p.kind == "leaf"]
        self.screens = screen_holes(design) if self.leaves else []
        self.ts = {"t": [], "free": [], "bonds": [], "largest": [], "blind": []}
        self.pyramidal = m.opt.cone == mujoco.mjtCone.mjCONE_PYRAMIDAL
        self.d0 = d
        return self

    def step(self, m, d, i):
        """After mj_step i: break the bonds over their limit, log peak contact forces, sample the timeseries."""
        n = d.nefc
        rows = np.flatnonzero(d.efc_type[:n] == EQ_ROW)
        if len(rows):
            eq = d.efc_id[rows]
            f2 = d.efc_force[rows] ** 2
            first = np.r_[True, eq[1:] != eq[:-1]]
            grp = np.cumsum(first) - 1
            k_in = np.arange(len(rows)) - np.flatnonzero(first)[grp]
            ids = eq[first]
            fpos = np.sqrt(np.bincount(grp, weights=np.where(k_in < 3, f2, 0.0)))
            bond = self.eq_bond[ids]
            ok = bond >= 0
            bond, load = bond[ok], fpos[ok]
            if self.opt["type"] == "weld":
                trot = np.sqrt(np.bincount(grp, weights=np.where(k_in >= 3, f2, 0.0)))[ok]
                load = np.maximum(load, trot / self.r_pair[bond])
            if i < self.n_settle:           # the settle sets the clump down; it doesn't count, and nothing breaks
                return self._contacts(m, d, i)
            self.peak_load[bond] = np.maximum(self.peak_load[bond], load)
            w = 0.0
            if self.sp is not None:
                w = 0.5 * (self.sp.wet[self.ba[bond]] + self.sp.wet[self.bb[bond]])
            limit = self.f_dry[bond] * (1.0 - self.opt["k_wet"] * w)
            brk = bond[load > limit]
            if len(brk):
                d.eq_active[self.eq[brk]] = 0
                self.live[brk] = False
                self.t_break[brk] = d.time
                self.load_at_break[brk] = load[load > limit]
                self.bonded[:] = False
                self.bonded[self.body[~self.free_mask()]] = True
        self._contacts(m, d, i)

    def _contacts(self, m, d, i):
        """Peak contact normal force per body, and the timeseries sample."""
        if d.ncon:
            con = d.contact
            adr, dim = con.efc_address[:d.ncon], con.dim[:d.ncon]
            use = adr >= 0
            if use.any():
                adr, dim, geom = adr[use], dim[use], con.geom[:d.ncon][use]
                if self.pyramidal:
                    nrow = np.where(dim == 1, 1, 2 * (dim - 1))
                    starts = np.r_[0, np.cumsum(nrow)[:-1]]
                    idx = np.repeat(adr - starts, nrow) + np.arange(nrow.sum())
                    fn = np.add.reduceat(d.efc_force[idx], starts)
                else:
                    fn = d.efc_force[adr]
                peak = self.peak if i >= self.n_settle else self.peak_settle
                for side in (0, 1):
                    b = m.geom_bodyid[geom[:, side]]
                    np.maximum.at(peak, b, fn)
                    if i >= self.n_settle:
                        on = self.bonded[b]
                        np.maximum.at(self.peak_bonded, b[on], fn[on])
        if i % self.every == 0:
            self.sample(d)

    def clusters(self):
        """Component label of each clump particle over the live bonds."""
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import connected_components
        n = len(self.particles)
        a, b = self.a[self.live], self.b[self.live]
        g = coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n))
        return connected_components(g, directed=False)[1]

    def free_mask(self):
        bonded = np.zeros(len(self.particles), bool)
        bonded[self.a[self.live]] = bonded[self.b[self.live]] = True
        return ~bonded

    def largest(self):
        lab = self.clusters()[self.is_spec]
        return int(np.bincount(lab).max()) if len(lab) else 0

    def blinding(self, d):
        """{screen zone: share of its holes under a leaf lying on it}."""
        out = {}
        for zone, z_top, holes in self.screens:
            covered = np.zeros(len(holes), bool)
            if self.rock is not None:
                j = self.rock.zone_level[zone]
                lp, lm = d.xpos[self.rock.body[j]], d.xmat[self.rock.body[j]].reshape(3, 3)
            else:
                lp, lm = np.zeros(3), np.eye(3)
            for b, (hx, hy) in self.leaves:
                R = lm.T @ d.xmat[b].reshape(3, 3)           # leaf axes in the level's frame
                c = (d.xpos[b] - lp) @ lm
                if abs(R[2, 2]) < np.cos(np.radians(BLIND_TILT_DEG)) or not (z_top - 1.0 <= c[2] <= z_top + BLIND_DZ):
                    continue
                corners = np.array([c + R @ np.array([sx * hx, sy * hy, 0.0])
                                    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))])[:, :2]
                e = np.roll(corners, -1, axis=0) - corners
                rel = holes[:, None, :] - corners[None]
                cross = e[None, :, 0] * rel[..., 1] - e[None, :, 1] * rel[..., 0]
                covered |= np.all(cross >= 0, axis=1) | np.all(cross <= 0, axis=1)
            out[zone] = round(float(covered.mean()), 4) if len(holes) else None
        return out

    def sample(self, d):
        free = self.free_mask()[self.is_spec]
        self.ts["t"].append(round(d.time - self.n_settle * self.dt, 4))
        self.ts["free"].append(round(float(free.mean()), 4))
        self.ts["bonds"].append(int(self.live.sum()))
        self.ts["largest"].append(self.largest())
        self.ts["blind"].append(self.blinding(d) if self.screens else {})

    # ---------- results ----------
    def metrics(self, plist, d=None):
        d = d or self.d0
        self.sample(d)
        t_shake0 = self.n_settle * self.dt
        spec_idx = np.flatnonzero(self.is_spec)
        # a specimen is freed when its last bond breaks; never bonded = free from the start
        t_free = np.full(len(self.particles), -np.inf)
        for k in range(len(self.pairs)):
            for i in (self.a[k], self.b[k]):
                t_free[i] = max(t_free[i], np.inf if self.live[k] else self.t_break[k] - t_shake0)
        tf = np.sort(t_free[spec_idx])

        def t_frac(q):
            k = int(np.ceil(q * len(tf))) - 1
            return None if not len(tf) or not np.isfinite(tf[k]) else round(float(max(tf[k], 0.0)), 4)

        fs = self.peak[self.body[spec_idx]] / 1000.0    # mN
        fb = self.peak_bonded[self.body[spec_idx]] / 1000.0
        fr = self.opt["fragile_mN"]
        mine = plist[self.offset:]
        sort = {}
        for k in self.kinds:
            sel = [p for p, s in zip(mine, self.is_spec) if s and p["kind"] == k]
            if sel:
                sort[k] = {"n": len(sel), "ideal": round(float(np.mean([p["final_zone"] == p["ideal_zone"] for p in sel])), 4),
                           "zones": {z: sum(p["final_zone"] == z for p in sel) for z in dict.fromkeys(p["final_zone"] for p in sel)}}
        debris = {}
        for k in DEBRIS:
            sel = [p for p in mine if p["kind"] == k]
            if sel:
                debris[k] = {z: sum(p["final_zone"] == z for p in sel) for z in dict.fromkeys(p["final_zone"] for p in sel)}
        settle_broken = int(np.sum(self.t_break < t_shake0))
        return {
            "spec": self.spec, "sigma_uN_per_mm": self.sigma,
            "n_specimens": int(self.is_spec.sum()), "n_debris": int((~self.is_spec).sum()),
            "diameter_mm": round(2 * self.core_r, 2), "envelope_mm": round(2 * self.radius, 2), "n_bonds": len(self.pairs),
            "bonds_per_specimen": round(float(np.mean(np.bincount(np.r_[self.a, self.b], minlength=len(self.particles))[spec_idx])), 2),
            "bond_mN": {"p10": round(float(np.percentile(self.f_dry, 10)) / 1000, 4),
                        "p50": round(float(np.median(self.f_dry)) / 1000, 4),
                        "p90": round(float(np.percentile(self.f_dry, 90)) / 1000, 4)} if len(self.f_dry) else None,
            "broken": int((~self.live).sum()), "broken_in_settle": settle_broken,
            "free_frac": self.ts["free"][-1], "t50_s": t_frac(0.5), "t90_s": t_frac(0.9),
            "largest_cluster": self.ts["largest"][-1],
            "unbonded_at_start": int(np.sum(t_free[spec_idx] == -np.inf)), "pack_overlap_mm": round(self.overlap, 4),
            "damage": {"fragile_mN": fr, "p50_mN": round(float(np.median(fs)), 4), "p90_mN": round(float(np.percentile(fs, 90)), 4),
                       "max_mN": round(float(fs.max()), 4), "share_over": round(float(np.mean(fs > fr)), 4),
                       "share_over_x": {str(x): round(float(np.mean(fs > x)), 4) for x in (1, 2, 5, 10, 20)},
                       "settle_max_mN": round(float(self.peak_settle[self.body[spec_idx]].max()) / 1000, 4),
                       "bonded_p90_mN": round(float(np.percentile(fb, 90)), 4), "bonded_max_mN": round(float(fb.max()), 4),
                       "bonded_share_over": round(float(np.mean(fb > fr)), 4),
                       "per_specimen_mN": [round(float(v), 3) for v in fs]},
            "blinding": self.ts["blind"][-1], "sort": sort, "debris_zones": debris,
            "bonds": [[int(a), int(b), None if np.isnan(t) else round(float(t - t_shake0), 4), round(float(pk) / 1000, 4), round(float(r), 4)]
                      for a, b, t, pk, r in zip(self.a, self.b, self.t_break, self.peak_load, self.r_pair)],
            "timeseries": self.ts,
        }


def summary(c):
    """One printed line for a run's results["clumps"]."""
    dmg = c["damage"]
    blind = ", ".join(f"{z} {v:.0%}" for z, v in c["blinding"].items() if v is not None) or "-"
    return (f"  clump: {c['n_specimens']} specimens + {c['n_debris']} debris, {c['diameter_mm']:g} mm, {c['n_bonds']} bonds "
            f"({c['spec']['bond']}): free {c['free_frac']:.0%}, t50 {c['t50_s']} s, t90 {c['t90_s']} s, largest cluster "
            f"{c['largest_cluster']}; broken in the settle {c['broken_in_settle']}; peak force p90 {dmg['p90_mN']:.2f} mN "
            f"(in the clump {dmg['bonded_p90_mN']:.2f}), over {dmg['fragile_mN']:g} mN {dmg['share_over']:.0%} "
            f"(in the clump {dmg['bonded_share_over']:.0%}); leaf blinding {blind}; packing overlap {c['pack_overlap_mm']} mm")


if __name__ == "__main__":
    spec = parse(sys.argv[1] if len(sys.argv) > 1 else "rice=50,quinoa=50,pasta=6,leaf=1,twig=2,dirt=10")
    cl = Clumps(spec, np.random.default_rng(0))
    hw = np.bincount(np.r_[cl.a, cl.b], minlength=len(cl.particles))
    print(f"{len(cl.particles)} bodies ({int(cl.is_spec.sum())} specimens), diameter {2 * cl.core_r:.1f} mm "
          f"(with debris {2 * cl.radius:.1f}), "
          f"{len(cl.pairs)} bonds, {hw[cl.is_spec].mean():.1f} per specimen (min {hw[cl.is_spec].min()}), "
          f"sigma {cl.sigma:g} uN/mm, bond strength p50 {np.median(cl.f_dry) / 1000:.3f} mN")
    for k in cl.kinds:
        sel = [i for i, p in enumerate(cl.particles) if p.kind == k]
        print(f"  {k:16s} {len(sel):3d}  bonds each {hw[sel].mean():.1f}")
