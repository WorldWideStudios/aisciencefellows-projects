"""Pantry grains for the sorter sim: the bench calibration set. Units mm, g, s.

Sizes are typical values until the team's caliper measurements replace them: once
bench/grain_dims.csv has at least MIN_MEASURED rows of a kind, that kind's mean size, spread and
density come from the measurements. Each dimension varies by the kind's relative spread (SPREAD,
else SD), clipped to +/-20% (CLIP sets a wider range for a few kinds).

    rice        white long-grain, an ellipsoid
    quinoa      a lens: round, flat ellipsoid
    chickpea    a near-round ellipsoid
    pasta       ditalini: a short tube of 8 boxes, open at both ends
    brown_rice  long-grain brown rice, an ellipsoid
    black_rice  short/medium-grain pigmented rice (black, some mahogany red), a plump ellipsoid
    wild_rice   Zizania: a long thin needle, one capsule along x
    chia        chia seed, a small flattened ellipsoid
    couscous    durum semolina granules, an ellipsoid; one size draw scales the whole grain (SIZE_LINKED)
    white_rice  white long-grain rice as photographed (US spec size): longer, wider and heavier than rice

rice, quinoa, chickpea and pasta are FROZEN: the design optimizer's leaderboard was run with them,
so their numbers and code paths stay as they are. The other kinds come from the team's pantry
photo of 2026-10-25. GRAINS.md has every kind's sources, assumptions and photo identification.

Run from sim\\ to print one of each:  <venv python> grains.py
"""
import csv
from pathlib import Path

import numpy as np
from common import Particle

SD = 0.07
# Relative spread per kind: one value, or one per dimension (length, width, thickness). SD for the
# rest. Bench measurements replace it (load_measured). Values and sources: GRAINS.md.
SPREAD = {
    "brown_rice": (0.047, 0.072, 0.05),
    "black_rice": 0.05,
    "wild_rice": (0.17, 0.08, 0.08),
    "chia": 0.055,
    "couscous": (0.15, 0.22, 0.105),
}
CLIP = {"wild_rice": (0.7, 1.3), "couscous": (0.6, 1.4)}   # relative range per kind; (0.8, 1.2) for the rest
# Kinds whose width draw is the grain's overall size: it scales all three dimensions, and the length
# and thickness draws are shape noise on L/W and T/W. Their SPREAD is (CV of L/W, CV of W, CV of T/W).
# Independent per-axis draws would average out in any combined size, such as the hole a grain passes.
SIZE_LINKED = ("couscous",)
# kind: ((length, width, thickness) mm, density g/mm^3, rgba). Pasta: (outer diameter, outer diameter, length).
# Wild rice: the kernel's (length, width, thickness); make() builds a round capsule of diameter
# sqrt(width * thickness). Densities of the new kinds are mass / shape volume (volume()).
SIZES = {
    "rice": ((6.5, 2.0, 1.7), 1.45e-3, "0.96 0.95 0.88 1"),
    "quinoa": ((2.0, 2.0, 1.1), 1.20e-3, "0.82 0.62 0.38 1"),
    "chickpea": ((8.5, 8.0, 7.5), 1.30e-3, "0.88 0.76 0.42 1"),
    "pasta": ((6.5, 6.5, 6.0), 1.45e-3, "0.97 0.70 0.20 1"),
    "brown_rice": ((7.2, 2.2, 1.85), 1.37e-3, "0.86 0.76 0.63 1"),
    "black_rice": ((5.5, 2.7, 1.95), 1.25e-3, "0.33 0.24 0.21 1"),
    "wild_rice": ((10.0, 1.85, 1.6), 1.28e-3, "0.19 0.15 0.12 1"),
    "chia": ((2.11, 1.32, 0.81), 1.12e-3, "0.34 0.32 0.30 1"),
    "couscous": ((2.15, 1.6, 1.3), 1.29e-3, "0.94 0.86 0.66 1"),
    "white_rice": ((7.2, 2.1, 1.7), 1.56e-3, "0.97 0.94 0.92 1"),
}
FROZEN = ("rice", "quinoa", "chickpea", "pasta")
PASTA_WALL = 1.2
PASTA_SEGMENTS = 8
KINDS = tuple(SIZES)
MEASURED = Path(__file__).resolve().parent / "bench" / "grain_dims.csv"
MIN_MEASURED = 5             # grains of a kind needed before the measurements replace SIZES


def volume(kind, dims):
    """Shape volume (mm^3) of a kind at dims (length, width, thickness), as make() builds it.
    Pasta is left out: its density is never fitted."""
    if kind == "wild_rice":
        r = np.sqrt(dims[1] * dims[2]) / 2
        return float(np.pi * r * r * (dims[0] - 2 * r) + 4 / 3 * np.pi * r ** 3)
    return float(np.pi / 6 * np.prod(dims))


def load_measured(path=MEASURED):
    """Replace SIZES and SPREAD with bench measurements where a kind has MIN_MEASURED rows: mean size,
    the relative spread, and density from mass over shape volume (pasta keeps its density; the FROZEN
    kinds use the volume at the mean size, the others the mean volume per grain).
    The FROZEN kinds get one spread, the mean over the three dimensions; the others one per dimension,
    and the SIZE_LINKED kinds (CV of L/W, CV of W, CV of T/W).
    Returns the kinds that changed."""
    if not path.exists():
        return []
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["kind"] in SIZES and r.get("length_mm")]
    changed = []
    for kind in SIZES:
        d = np.array([[float(r[k]) for k in ("length_mm", "width_mm", "thickness_mm")] for r in rows if r["kind"] == kind])
        if len(d) < MIN_MEASURED:
            continue
        mean = d.mean(axis=0)
        rel = d.std(axis=0) / mean
        if kind in SIZE_LINKED:
            shape = np.stack([d[:, 0] / d[:, 1], d[:, 1], d[:, 2] / d[:, 1]], axis=1)
            rel = shape.std(axis=0) / shape.mean(axis=0)
        SPREAD[kind] = float(np.mean(rel)) if kind in FROZEN else tuple(float(v) for v in rel.round(4))
        density = SIZES[kind][1]
        masses = [float(r["mass_mg"]) for r in rows if r["kind"] == kind and r.get("mass_mg")]
        if masses and kind != "pasta":
            # new kinds: the mean volume per grain, which stays right when sizes are correlated
            # (couscous: one size draw scales L, W and T, so the volume at the mean size is ~15% low)
            vol = volume(kind, mean) if kind in FROZEN else np.mean([volume(kind, row) for row in d])
            density = np.mean(masses) * 1e-3 / vol
        SIZES[kind] = (tuple(mean.round(3)), float(density), SIZES[kind][2])
        changed.append(kind)
    return changed


load_measured()


def make(kind, rng, size_scale=1.0):
    base, density, rgba = SIZES[kind]
    lo, hi = CLIP.get(kind, (0.8, 1.2))
    f = np.clip(rng.normal(1.0, SPREAD.get(kind, SD), 3), lo, hi)
    if kind in SIZE_LINKED:      # the width factor is the size; length and thickness keep their shape around it
        f[[0, 2]] *= f[1]
    d = np.array(base) * size_scale * f
    if kind == "quinoa":
        d[1] = d[0]
    if kind == "pasta":
        d[1] = d[0]
        r_out, half_len = d[0] / 2, d[2] / 2
        seg = np.pi / PASTA_SEGMENTS
        geoms = []
        for k in range(PASTA_SEGMENTS):
            a = 2 * seg * k
            r_mid = r_out - PASTA_WALL / 2
            geoms.append(
                f'<geom type="box" size="{PASTA_WALL / 2:.4f} {r_out * np.tan(seg):.4f} {half_len:.4f}" '
                f'pos="{r_mid * np.cos(a):.4f} {r_mid * np.sin(a):.4f} 0" quat="{np.cos(a / 2):.5f} 0 0 {np.sin(a / 2):.5f}" '
                f'density="{density}" rgba="{rgba}"/>')
        xml = "".join(geoms)
    elif kind == "wild_rice":   # round section with the kernel's width x thickness area; tip to tip = length
        diameter = np.sqrt(d[1] * d[2])
        half = d[0] / 2 - diameter / 2
        xml = (f'<geom type="capsule" fromto="{-half:.4f} 0 0 {half:.4f} 0 0" size="{diameter / 2:.4f}" '
               f'density="{density}" rgba="{rgba}"/>')
        d = np.array([d[0], diameter, diameter])
    else:
        xml = f'<geom type="ellipsoid" size="{d[0] / 2:.4f} {d[1] / 2:.4f} {d[2] / 2:.4f}" density="{density}" rgba="{rgba}"/>'
    length, width, thickness = sorted(d, reverse=True)
    span = float(np.hypot(d[0], d[2])) if kind == "pasta" else float(length)
    return Particle(kind, "grain", xml, {"length": float(length), "width": float(width),
                                         "thickness": float(thickness), "span": span})


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    print("measured kinds from", MEASURED.name, ":", load_measured() or "none yet")
    for kind in KINDS:
        p = make(kind, rng)
        print(kind, {k: round(v, 2) for k, v in p.dims.items()})
    print("mass at the mean size, mg:", {k: round(SIZES[k][1] * volume(k, SIZES[k][0]) * 1e3, 2)
                                         for k in KINDS if k != "pasta"})
