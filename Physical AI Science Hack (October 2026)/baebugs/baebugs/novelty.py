"""Select for novelty.

1. Novel sizes - bodies in low-density regions of (log length, log width,
   aspect) relative to a reference set (past runs, Essig-derived prior, kit
   analogs). k-NN distance against the reference, scored as a percentile of the
   reference's own k-NN distances, so 'novel' adapts to how spread the reference is.
2. Mesh gaps - novel bodies whose width falls between inventory apertures, so the
   current stack would lump them with something else.
3. Filter suggestions - for each gap, rank in-kit materials (procurable ones only
   with include_procurable=True; the Track A kit is limited) by
   how well they split the gap AND by preservation risk for the specimen profile.
"""
from __future__ import annotations

import itertools

import numpy as np

from .preservation import gentlest_settings, worst
from .sieve import load_yaml


def _feats(lengths, widths):
    L, W = np.asarray(lengths, float), np.asarray(widths, float)
    return np.c_[np.log(L), np.log(W), W / np.maximum(L, 1e-9)]


def _knn(a, b, k, exclude_self=False):
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    if exclude_self:
        np.fill_diagonal(d, np.inf)
    return np.sort(d, axis=1)[:, :k].mean(axis=1)


def novel_sizes(lengths, widths, ref_lengths, ref_widths, k=5, pct=99.0, factor=1.25):
    x, r = _feats(lengths, widths), _feats(ref_lengths, ref_widths)
    k = max(1, min(k, len(r) - 1))
    ref_d = _knn(r, r, k, exclude_self=True)
    d = _knn(x, r, k)
    cut = np.percentile(ref_d, pct) * factor
    score = np.searchsorted(np.sort(ref_d), d) / len(ref_d)
    return [{"i": i, "length_mm": float(lengths[i]), "width_mm": float(widths[i]),
             "novelty": float(score[i]), "novel": bool(d[i] > cut)}
            for i in range(len(d))]


def mesh_gaps(widths, apertures, margin=1.1, min_rel_gap=0.35):
    """Group widths by which pair of inventory meshes they fall between and
    report gaps wide enough (relative) that a new mesh would split them."""
    cuts = sorted([a * margin for a in apertures if a > 0], reverse=True)
    bounds = [np.inf] + cuts + [0.0]
    out = []
    for hi, lo in itertools.pairwise(bounds):
        inside = [w for w in widths if lo <= w < hi]
        if not inside:
            continue
        top = hi if np.isfinite(hi) else max(inside) * 1.2
        rel = (top - lo) / max(top, 1e-9)
        if rel >= min_rel_gap:
            out.append({"between_mm": [round(lo, 3), round(float(top), 3)],
                        "widths": sorted(inside), "rel_gap": round(float(rel), 2)})
    return out


def suggest_filters(gap: dict, profile: str, preservation="ethanol_70",
                    margin=1.1, top=3, include_procurable=False, cfg=None):
    cfg = cfg or load_yaml("materials.yaml")
    ws = np.asarray(gap["widths"])
    # isolate the novel cluster: retain all of it, pass everything smaller
    target = float(np.min(ws)) / margin
    lo, hi = gap["between_mm"]
    ranked = []
    for m in cfg["materials"]:
        a = m["aperture_mm"]
        if a <= 0 or not (lo / margin < a < hi / margin):
            continue
        if not include_procurable and not m["in_kit"]:
            continue
        split = 1 - abs(np.log(a / target))       # 1 = aperture right under the cluster
        retained = int((ws >= a * margin).sum())
        settings = gentlest_settings(profile, m, preservation, cfg=cfg)
        part, risk = worst(profile, m, preservation=preservation, cfg=cfg,
                           **({"flow_l_per_min": settings["flow"],
                               "agitation": settings["agitation"]} if settings else {}))
        score = split - 1.5 * risk - (0.0 if m["in_kit"] else 0.1)
        ranked.append({"material": m["id"], "family": m["family"], "aperture_mm": a,
                       "in_kit": m["in_kit"], "split_quality": round(float(split), 2),
                       "retains": f"{retained}/{len(ws)}", "worst_part": part,
                       "damage_risk": risk, "gentle_settings": settings,
                       "score": round(float(score), 3)})
    ranked.sort(key=lambda r: -r["score"])
    if not ranked:
        ranked = [{"material": "FABRICATE", "aperture_mm": round(target, 3),
                   "note": "no inventory material splits this gap; print a smooth "
                           "chamfered grid or buy monofilament nylon at this aperture"}]
    return ranked[:top]
