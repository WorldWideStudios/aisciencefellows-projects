"""Extend the therapeutics-view capsid set with 100 synthetic variants.

Rationale: the v1_release candidate pool holds 120 sequences and we've already
evaluated 85 unique of them across the RL + random campaigns. To give the
Pareto-therapeutics scatter more density (and more Pareto-optimal candidates
to inspect) we generate 100 additional plausible AAV2 variants — mixing
substitution-only, insertion-only, and stacked (7-mer + subs) classes — score
each through the SAME simulator (dmd_wet_lab_simulator.simulate_dmd_assay), and
append them to both workbench JSONs.

The new variants carry selection_strategy='extended_pool' so the UI can toggle
them independently of the RL/random/seed sets.

Writes:
  workbench/capsid_pareto_data.json  (rewritten with combined rows)
  workbench/capsid_details.json      (appended with new detail entries)

Usage:
    ~/venv/bin/python -m aav_optimization.expand_capsid_pool
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "aav_optimization"))
import dmd_config as config
sys.path.insert(0, str(REPO))
from aav_optimization.pipeline.dmd_wet_lab_simulator import simulate_dmd_assay

CAPSID_PARETO_JSON  = REPO / "workbench" / "capsid_pareto_data.json"
CAPSID_DETAILS_JSON = REPO / "workbench" / "capsid_details.json"

VP1_LENGTH = 735
REFERENCE_PEPTIDE = "ASSLNIA"
INS_SITE_LABEL = "between VP1 residue 587 and 588 (VR-VIII surface loop)"

# VR-loop residue ranges (AAV2 VP1 numbering). Substitutions target these
# surface loops because they drive tropism + immune evasion — matches the
# distribution observed in the v1_release pool.
VR_LOOPS = {
    "VR-I":    (263, 268),
    "VR-IV":   (449, 468),
    "VR-V":    (488, 505),
    "VR-VIII": (581, 593),
    "VR-IX":   (704, 714),
}
SUB_TARGET_LOOPS = ["VR-IV", "VR-V", "VR-IX"]   # avoid VR-VIII when doing insertions
AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"

# Peptide alphabet biased toward ASSLNIA-like sequences for the muscle-tropic
# insertion class + a random pool for exploration. Distribution mirrors the
# existing v1_release insertion library.
ASSLNIA_LIKE = [
    "ASSLNIA", "ASSLNTA", "ASSMNIA", "PSSLNIA", "ASSLNIS",
    "LALGETTRP", "LAGETTRP", "ALGETRP", "ALGETRS", "ANGETLP",
    "NLAGETT", "LIGETRH", "LAGGTTP", "ALSETRP", "RAATPNS",
    "ARAATPN", "PGSLNIA", "SSLNIAG", "SGLNIAP", "TSLNIAG",
]
RANDOM_INS_ALPHABET = "ACDEFGHIKLMNPQRSTVWY"


def _rand_peptide(rng: random.Random, length: int) -> str:
    return "".join(rng.choices(RANDOM_INS_ALPHABET, k=length))


def _rand_sub(rng: random.Random, resi: int, wt_placeholder: str = "X") -> dict:
    mut = rng.choice([a for a in AMINO_ACIDS if a != wt_placeholder])
    return {"resi": resi, "wt": wt_placeholder, "mut": mut}


def _sub_ids_from_ranges(rng: random.Random, n_subs: int) -> list[dict]:
    """Sample `n_subs` unique residue positions from the sub-target VR loops."""
    positions: set[int] = set()
    while len(positions) < n_subs:
        loop = rng.choice(SUB_TARGET_LOOPS)
        lo, hi = VR_LOOPS[loop]
        positions.add(rng.randint(lo, hi))
    return [_rand_sub(rng, r, wt_placeholder="X") for r in sorted(positions)]


def _hash_id(payload: str) -> str:
    return hashlib.sha1(payload.encode()).hexdigest()[:8]


def _classify_vr_region(resi: int) -> str:
    for name, (lo, hi) in VR_LOOPS.items():
        if lo <= resi <= hi:
            return name
    return "backbone"


def _generate_variant(rng: random.Random, variant_class: str) -> dict:
    """Generate a synthetic variant dict compatible with simulate_dmd_assay
    inputs + the workbench JSON schemas."""
    if variant_class == "substitution":
        n_subs = rng.choice([3, 4, 5, 6, 7])
        subs = _sub_ids_from_ranges(rng, n_subs)
        insertion = None
    elif variant_class == "insertion":
        subs = []
        insertion = rng.choice(ASSLNIA_LIKE + [_rand_peptide(rng, 7),
                                                _rand_peptide(rng, 8),
                                                _rand_peptide(rng, 9)])
    else:   # stacked = insertion + 2..5 subs
        subs = _sub_ids_from_ranges(rng, rng.choice([2, 3, 4, 5]))
        insertion = rng.choice(ASSLNIA_LIKE + [_rand_peptide(rng, 7)])
    ins_len = len(insertion) if insertion else 0
    hamming = len(subs) + ins_len

    return {
        "variant_class": variant_class,
        "insertion":     insertion,
        "insertion_len": ins_len,
        "subs":          subs,
        "hamming":       hamming,
    }


def _sub_str(subs: list[dict]) -> str:
    return ",".join(f"{s['wt']}{s['resi']}{s['mut']}" for s in subs)


def _mutation_str(v: dict) -> str:
    parts = []
    if v["insertion"]:
        parts.append(f"ins587_588:{v['insertion']}")
    if v["subs"]:
        parts.append(_sub_str(v["subs"]))
    return "+".join(parts)


def _score(v: dict, rng_np: np.random.Generator) -> dict:
    out = simulate_dmd_assay(
        has_7mer_insertion=v["insertion_len"] > 0,
        insertion_peptide=v["insertion"],
        insertion_length=v["insertion_len"],
        hamming_to_aav2=v["hamming"],
        rng=rng_np,
    )
    return {
        "mt":  round(out["muscle_transduction"], 6),
        "ne":  round(out["nab_escape"],           6),
        "hep": round(out["hepatotoxicity_score"], 6),
        "ok":  bool(out["hepatotoxicity_score"] < config.HEPATOTOX_THRESHOLD),
    }


def _pareto_flags(rows: list[dict]) -> None:
    """Set r['front']=True for constraint-passing rows that dominate no
    other constraint-passing row on (mt, ne)."""
    for r in rows:
        r["front"] = False
    passing = [r for r in rows if r["ok"]]
    for i, r in enumerate(passing):
        dominated = False
        for j, q in enumerate(passing):
            if i == j: continue
            if q["mt"] >= r["mt"] and q["ne"] >= r["ne"] and (q["mt"] > r["mt"] or q["ne"] > r["ne"]):
                dominated = True; break
        if not dominated:
            r["front"] = True


def main(n_new: int = 100, seed: int = 42) -> None:
    print(f"=== Extend capsid pool with {n_new} synthetic variants ===\n")
    rng = random.Random(seed)
    rng_np = np.random.default_rng(seed)

    pareto = json.loads(CAPSID_PARETO_JSON.read_text())
    details = json.loads(CAPSID_DETAILS_JSON.read_text())
    existing_ids = {r["id"] for r in pareto["rows"]}
    print(f"  Existing rows: {len(pareto['rows'])} · unique ids: {len(existing_ids)}")

    # Class mix mirrors the v1_release pool distribution (~30% sub, 20% ins, 50% stacked)
    class_choices = (["substitution"] * 30 + ["insertion"] * 20 + ["stacked"] * 50)
    new_rows: list[dict] = []
    new_detail: dict[str, dict] = {}
    attempts = 0
    while len(new_rows) < n_new and attempts < n_new * 10:
        attempts += 1
        vc = rng.choice(class_choices)
        v = _generate_variant(rng, vc)
        cid = _hash_id(_mutation_str(v))
        if cid in existing_ids or cid in {r["id"] for r in new_rows}:
            continue

        s = _score(v, rng_np)
        new_rows.append({
            "id":     cid,
            "mt":     s["mt"],
            "ne":     s["ne"],
            "hep":    s["hep"],
            "ok":     s["ok"],
            "front":  False,           # recomputed after append
            "strat":  "extended_pool",
            "cycle":  -1,
            "hyps":   [],
        })
        # Substitution regions
        sub_regions: dict[str, list[dict]] = {}
        for sub in v["subs"]:
            sub_regions.setdefault(_classify_vr_region(sub["resi"]), []).append(sub)
        peptide_sim = 0.0
        if v["insertion"]:
            n = min(len(v["insertion"]), len(REFERENCE_PEPTIDE))
            if n:
                peptide_sim = sum(1 for a, b in zip(v["insertion"][:n], REFERENCE_PEPTIDE[:n])
                                  if a == b) / n
        new_detail[cid] = {
            "capsid_id": cid,
            "class":     v["variant_class"],
            "hamming":   v["hamming"],
            "delta_pct": round(100.0 * v["hamming"] / VP1_LENGTH, 2),
            "vp1_length": VP1_LENGTH,
            "insertion": v["insertion"],
            "insertion_length": v["insertion_len"],
            "insertion_site": INS_SITE_LABEL,
            "reference_peptide": REFERENCE_PEPTIDE,
            "peptide_similarity_to_ref": round(peptide_sim, 3),
            "substitutions": v["subs"],
            "sub_regions":   sub_regions,
            "mutation_str":  _mutation_str(v),
            "synthetic":     True,
        }

    print(f"  Generated {len(new_rows)} new variants in {attempts} attempts")

    combined = pareto["rows"] + new_rows
    _pareto_flags(combined)
    pareto["rows"] = combined
    n_front = sum(1 for r in combined if r["front"])
    n_new_front = sum(1 for r in new_rows if r["front"])
    print(f"  Combined rows: {len(combined)}  ·  Pareto-optimal: {n_front} ({n_new_front} from new)")

    CAPSID_PARETO_JSON.write_text(json.dumps(pareto))
    details.update(new_detail)
    CAPSID_DETAILS_JSON.write_text(json.dumps(details, indent=2))
    print(f"\nWrote {CAPSID_PARETO_JSON.name} ({len(combined)} rows)")
    print(f"Wrote {CAPSID_DETAILS_JSON.name} ({len(details)} detail entries)")


if __name__ == "__main__":
    main()
