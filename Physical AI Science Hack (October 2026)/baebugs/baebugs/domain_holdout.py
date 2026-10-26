"""Source-domain sets for DAISY-BB-002: one pseudo-labelled set per US state.

For each state (gbif_az, gbif_nv, gbif_or) the same YOLOE ruler-scaled teacher used for
pseudo_specimens_r3_real labels the photos, after EXCLUDING every image already used
elsewhere, so a held-out state never shares a specimen photo with training or evaluation:
  - by GBIF media id (filename stem) and by sha256, against pseudo_specimens_r3_real,
    _teacher_check, _teacher_check2 and _rejected_pseudo_v1;
  - byte-identical photos across states are kept once (first state in order wins);
  - undecodable images are skipped by the teacher and counted.
Each set is split 2/3 train, 1/3 val (val_every=3) so it can be held out (val) or
trained on (train) in leave-one-state-out runs. Everything is recorded in an exclusion
report; the sets are then verified and registered with baebugs.daisy_data.
Limitation: specimen identity is approximated by media id + bytes; two different photos of
one physical specimen under different GBIF records are not detected.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .retention import sha

STATES = ("az", "nv", "or")
EXCLUDE_SETS = ("pseudo_specimens_r3_real", "_teacher_check", "_teacher_check2", "_rejected_pseudo_v1")


def used_images(datasets):
    stems, shas = set(), set()
    for s in EXCLUDE_SETS:
        for f in Path(datasets, s).rglob("*.jpg"):
            stems.add(f.stem); shas.add(sha(f))
    return stems, shas


def select(datasets, states=STATES, work=None):
    """Hardlink the admissible photos of each state into work/<state>/; return the report."""
    datasets = Path(datasets); work = Path(work or datasets.parent / "work" / "holdout_src")
    stems, shas = used_images(datasets)
    seen, report = set(), {"excluded_sets": list(EXCLUDE_SETS), "states": {}}
    for st in states:
        src = datasets / f"gbif_{st}" / "images"
        dst = work / st; dst.mkdir(parents=True, exist_ok=True)
        r = {"photos": 0, "excluded_by_id": 0, "excluded_by_bytes": 0, "cross_state_duplicate": 0, "admitted": 0}
        for f in sorted(src.glob("*.jpg")):
            r["photos"] += 1
            h = sha(f)
            if f.stem in stems:
                r["excluded_by_id"] += 1; continue
            if h in shas:
                r["excluded_by_bytes"] += 1; continue
            if h in seen:
                r["cross_state_duplicate"] += 1; continue
            seen.add(h)
            t = dst / f.name
            if not t.exists():
                try:
                    os.link(f, t)
                except OSError:
                    import shutil
                    shutil.copy2(f, t)
            r["admitted"] += 1
        report["states"][st] = r
    return report, work


def build(datasets="/Volumes/magicBLACKbox/baebugs/datasets", states=STATES, max_images=None):
    from .train import pseudo_label_specimens
    report, work = select(datasets, states)
    for st in states:
        out = Path(datasets, f"holdout_{st}")
        stats = pseudo_label_specimens([work / st], out, val_every=3, max_images=max_images)
        report["states"][st]["teacher"] = stats
        report["states"][st]["status"] = "BUILT" if stats.get("kept_images") else "NOT_BUILT_TEACHER_KEPT_NONE"
        (out / "HOLDOUT_REPORT.json").write_text(json.dumps({"state": st, **report["states"][st],
                                                              "excluded_sets": report["excluded_sets"]}, indent=1))
        print(st, json.dumps(report["states"][st]), flush=True)
    Path(datasets, "holdout_report.json").write_text(json.dumps(report, indent=1))
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser("baebugs-domain-holdout")
    ap.add_argument("--datasets", default="/Volumes/magicBLACKbox/baebugs/datasets")
    ap.add_argument("--states", nargs="*", default=list(STATES))
    ap.add_argument("--max-images", type=int)
    a = ap.parse_args()
    build(a.datasets, tuple(a.states), a.max_images)
