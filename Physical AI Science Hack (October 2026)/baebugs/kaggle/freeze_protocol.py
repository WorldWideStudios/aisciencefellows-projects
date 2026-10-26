"""Freeze DAISY-BB-001.json from the verified dataset summary. Refuses to freeze
if any staged member is not VERIFIED. Pins the baebugs code commit (HEAD).

  python kaggle/freeze_protocol.py --datasets /Volumes/magicBLACKbox/baebugs/daisy/datasets.json
"""
import argparse
import json
import subprocess
from pathlib import Path

from baebugs.daisy_data import BUNDLES

SYN = ["synth_1_30_r2", "synth_1_30_r3_real", "synth_seg"]
PSE = ["pseudo_specimens_r3_real"]
MR = ["multires_mp_0.3", "multires_mp_1", "multires_mp_3"]


def runs():
    A, Bm, C = SYN, SYN + PSE, SYN + PSE + MR
    return [
        {"name": "A_synth", "train": A, "val": A},
        {"name": "B_synth_pseudo", "train": Bm, "val": Bm},
        {"name": "C_all", "train": C, "val": C},
        {"name": "LODO_synth", "train": PSE + MR, "val": SYN},
        {"name": "LODO_pseudo", "train": SYN + MR, "val": PSE},
        {"name": "LODO_multires", "train": SYN + PSE, "val": MR},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--out", default="daisy/DAISY-BB-001.json")
    a = ap.parse_args()
    s = json.loads(Path(a.datasets).read_text())
    ds = s["datasets"]
    bundles = {b: [m for m in ms if m in ds] for b, ms in BUNDLES.items()}
    need = {m for r in runs() for m in r["train"] + r["val"]} | {"toy_renders", "teacher_check", "teacher_check2"}
    bad = {m: ds.get(m, {}).get("status") for m in need if ds.get(m, {}).get("status") != "VERIFIED"}
    if bad:
        raise SystemExit(f"refusing to freeze: not VERIFIED {bad}")
    staged = {m for ms in bundles.values() for m in ms if ds[m]["status"] == "VERIFIED"}
    bundles = {b: [m for m in ms if m in staged] for b, ms in bundles.items()}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    proto = {"id": "DAISY-BB-001", "status": "PROPOSED", "baebugs_commit": commit,
             "datasets_root": s["root"], "roots": {m: ds[m]["merkle_root"] for m in sorted(staged)},
             "bundles": bundles, "runs": runs(),
             "settings": {"model": "yolo11n-seg.pt", "ultralytics": "8.4.188", "seed": 2026, "epochs": 15,
                          "imgsz": 640, "batch": 16, "workers": 4},
             "global_leakage": s["global_leakage"]}
    Path(a.out).write_text(json.dumps(proto, indent=1, sort_keys=True))
    print(a.out, commit, len(staged), "members")


if __name__ == "__main__":
    main()
