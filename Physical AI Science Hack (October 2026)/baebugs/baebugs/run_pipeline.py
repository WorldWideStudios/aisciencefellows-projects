"""End-to-end local training round with a Merkle break point (commit + push)
at every step and every epoch.

  python -m baebugs.run_pipeline --run r2 \
      --data-root /Volumes/magicBLACKbox/baebugs --venv-root /Volumes/magicLABbox/baebugs \
      --images DIR [DIR ...] --init-weights PATH --epochs 30

Steps (each one = ledger leaf -> git commit -> git push):
  data      snapshot of image sources (counts, manifest sha256)
  synth     1-30 mm synthetic set with mm ground truth
  pseudo    specimen-photo teacher: ruler-scaled, stage-only labels + silver mm truth
  mix       synthetic + pseudo-labelled real (no forgetting)
  fit       fit_start, epoch_001..N, fit_end (metrics + weight hashes)
  bench     mm accuracy on synthetic truth and on real silver truth
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .git_ledger import GitLedger, sha256_file


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs-pipeline")
    ap.add_argument("--run", required=True)
    ap.add_argument("--data-root", default="/Volumes/magicBLACKbox/baebugs")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--init-weights", default="yolo11n-seg.pt")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--n-synth", type=int, default=600)
    ap.add_argument("--max-images", type=int)
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)

    from .synth_seg import build_dataset
    from .train import bench, fit, mix, pseudo_label_specimens

    root = Path(a.data_root)
    led = GitLedger(a.run, a.repo, push=not a.no_push)

    # 1 data snapshot
    srcs = {}
    for d in a.images:
        d = Path(d)
        man = d.parent / "manifest.jsonl"
        srcs[str(d)] = {"images": sum(1 for _ in d.glob("*.jpg")),
                        "manifest_sha256": sha256_file(man) if man.exists() else None}
    led.append("data", {"sources": srcs, "total_images": sum(v["images"] for v in srcs.values())})

    # 2 synthetic 1-30 mm
    synth = root / "datasets" / f"synth_1_30_{a.run}"
    if not (synth / "data.yaml").exists():
        build_dataset(synth, a.n_synth, max(60, a.n_synth // 5))
    led.append("synth", {"dir": str(synth), "n_train": a.n_synth},
               files={"truth_val.json": synth / "truth_val.json"})

    # 3 pseudo-labels from real specimen photos
    pseudo = root / "datasets" / f"pseudo_specimens_{a.run}"
    stats = pseudo_label_specimens(a.images, pseudo, max_images=a.max_images)
    led.append("pseudo", stats, files={"truth_real_val.json": pseudo / "truth_real_val.json"})

    # 4 mix
    mixed = root / "datasets" / f"mix_{a.run}" / "data.yaml"
    sources = [synth / "data.yaml"] + ([pseudo / "data.yaml"] if stats.get("kept_images") else [])
    mix(sources, mixed)
    led.append("mix", {"sources": [str(s) for s in sources]}, files={"data.yaml": mixed})

    # 5 fit (one break point per epoch, from inside the trainer)
    best = fit(mixed, a.init_weights, a.epochs, batch=a.batch, project=str(root / "runs"),
               name=a.run, ledger=led)

    # 6 bench
    res = {"synthetic": bench(best, synth / "truth_val.json")}
    rv = pseudo / "truth_real_val.json"
    if rv.exists() and json.loads(rv.read_text()):
        res["real_silver"] = bench(best, rv)
    led.append("bench", res, files={"best.pt": best})
    print(json.dumps(res, indent=1))
    print("ledger verifies:", led.verify())


if __name__ == "__main__":
    main()
