"""Freeze DAISY-BB-002 (source-domain holdout) as preregistered in daisy/DAISY-BB-002-prereg.md
and amended (before any data/run) by daisy/DAISY-BB-002-prereg-amendment-1.md.

Inherits settings, gates and variance from DAISY-BB-001b unchanged; pins the prereg sha256,
the predecessor sha256 and the baebugs commit. Refuses to freeze unless every member used is
VERIFIED and, PER RUN, no train-split file of a train member is byte-identical to a val-split
file of any member evaluated in that run (pointer manifests). The global cross-dataset overlap is
recorded but not used: r3 itself still holds the out-of-state photos in its train split.

  python kaggle/freeze_002.py --datasets /Volumes/magicBLACKbox/baebugs/daisy/datasets.json
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from baebugs.daisy_data import BUNDLES

SYN = ["synth_1_30_r2", "synth_1_30_r3_real", "synth_seg"]
PSE = ["pseudo_specimens_r3_real"]
H = {s: f"holdout_{s}" for s in ("az", "nv", "or")}
USE = ["baebugs-daisy-train", "baebugs-daisy-eval", "baebugs-daisy-holdout"]


def runs():
    hold = list(H.values())
    return [{"name": "CA_only", "train": SYN + ["r3_ca"], "val": SYN + ["r3_ca"] + hold},
            {"name": "Synth_only", "train": SYN, "val": SYN + ["r3_ca"] + hold}]


def split_shas(manifests, name, split):
    f = Path(manifests, f"{name}.jsonl")
    return {l["sha256"] for l in map(json.loads, f.read_text().splitlines())
            if l["path"].startswith(f"images/{split}/")}


def split_ids(manifests, name, split):
    f = Path(manifests, f"{name}.jsonl")
    return {Path(l["path"]).stem for l in map(json.loads, f.read_text().splitlines())
            if l["path"].startswith(f"images/{split}/")}


def run_leakage(manifests, runs_):
    """byte level (sha) and media-id level (filename stem; synthetic members excluded from the id check)."""
    out = {}
    for r in runs_:
        tr = set().union(*(split_shas(manifests, m, "train") for m in r["train"]))
        va = set().union(*(split_shas(manifests, m, "val") for m in r["val"]))
        tri = set().union(*(split_ids(manifests, m, "train") for m in r["train"] if m not in SYN))
        vai = set().union(*(split_ids(manifests, m, "val") for m in r["val"] if m not in SYN))
        out[r["name"]] = {"train_files": len(tr), "val_files": len(va), "overlap": len(tr & va),
                          "train_ids": len(tri), "val_ids": len(vai), "id_overlap": len(tri & vai)}
    return out


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--out", default="daisy/DAISY-BB-002a.json")
    ap.add_argument("--id", default="DAISY-BB-002a")
    a = ap.parse_args()
    s = json.loads(Path(a.datasets).read_text()); ds = s["datasets"]
    need = {m for r in runs() for m in r["train"] + r["val"]} | {"toy_renders"}
    bad = {m: ds.get(m, {}).get("status") for m in need if ds.get(m, {}).get("status") != "VERIFIED"}
    if bad:
        raise SystemExit(f"refusing to freeze: not VERIFIED {bad}")
    leak = run_leakage(Path(a.datasets).parent / "manifests", runs())
    if any(v["overlap"] or v["id_overlap"] for v in leak.values()):
        raise SystemExit(f"refusing to freeze: per-run train/val overlap {leak}")
    bundles = {b: [m for m in BUNDLES[b] if ds.get(m, {}).get("status") == "VERIFIED"] for b in USE}
    staged = sorted({m for ms in bundles.values() for m in ms})
    prev = json.loads(Path("daisy/DAISY-BB-001b.json").read_text())
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    proto = {"id": a.id, "status": "PROPOSED", "baebugs_commit": commit,
             "preregistration": {"path": "daisy/DAISY-BB-002-prereg.md", "sha256": fsha("daisy/DAISY-BB-002-prereg.md"),
                                 "amendment_1": {"path": "daisy/DAISY-BB-002-prereg-amendment-1.md",
                                                 "sha256": fsha("daisy/DAISY-BB-002-prereg-amendment-1.md")},
                                 **({"amendment_2": {"path": "daisy/DAISY-BB-002-prereg-amendment-2.md",
                                                     "sha256": fsha("daisy/DAISY-BB-002-prereg-amendment-2.md")}}
                                    if a.id != "DAISY-BB-002" else {})},
             **({"amends": {"protocol": "DAISY-BB-002", "sha256": fsha("daisy/DAISY-BB-002.json"),
                            "reason": "002 never ran; r3 photo identity widened to media id + pixels (amendment 2)"}}
                if a.id != "DAISY-BB-002" else {}),
             "split_report": json.loads((Path(a.datasets).parents[1] / "datasets" / "domain_split_report.json").read_text()),
             "run_leakage": leak,
             "predecessor": {"protocol": "DAISY-BB-001b", "sha256": fsha("daisy/DAISY-BB-001b.json")},
             "datasets_root": s["root"], "roots": {m: ds[m]["merkle_root"] for m in staged},
             "bundles": bundles, "runs": runs(),
             "settings": prev["settings"], "gates": prev["gates"], "variance": prev["variance"],
             "global_leakage": {**s["global_leakage"], "note": "includes r3 (not used by any 002 run) vs holdouts"}}
    Path(a.out).write_text(json.dumps(proto, indent=1, sort_keys=True))
    print(a.out, commit, len(staged), "members")


if __name__ == "__main__":
    main()
