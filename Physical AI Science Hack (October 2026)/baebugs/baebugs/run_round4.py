"""Round 4: different megapixels + unknown-vs-novel triage + dashboard data.
Every step is a Merkle break point (commit + push); every epoch too.

  python -m baebugs.run_round4 --run r4_multires --data-root /Volumes/magicBLACKbox/baebugs \
      --init-weights <r3 best.pt> --pseudo <pseudo dir from r3> --synth <synth dir from r3> \
      --triage-images DIR [DIR ...] --epochs 15
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from .git_ledger import GitLedger


def run_triage(weights, image_dirs, ref_L, ref_W, out_jsonl, max_images=300):
    from .measure import YoloMeasurer, consensus
    from .specimen_photo import ruler_px_per_mm, segment_yoloe
    from .triage import summarize, triage, write_alerts
    student = YoloMeasurer(str(weights), conf=0.15)
    paths = [p for d in image_dirs for p in sorted(Path(d).glob("*.jpg"))][:max_images]
    allv, n_img, measured = [], 0, []
    for p in paths:
        img = cv2.imread(str(p))
        if img is None:
            continue
        ppm, conf = ruler_px_per_mm(img)
        if not ppm or conf < 0.4:
            continue                      # no trustworthy mm scale -> can't judge size novelty
        n_img += 1
        a = student(img, ppm)
        _, b = segment_yoloe(img, ppm)    # zero-shot teacher as the second opinion
        ms = consensus(a, b, ppm, match_mm=max(2.0, 0.5 * max([m.length_mm for m in a + b] or [2]))) \
            if (a or b) else []
        al = triage(ms, ref_L, ref_W, image=str(p))
        write_alerts(al, out_jsonl)
        allv += al
        measured += [{"length_mm": x.length_mm, "width_mm": x.width_mm, "status": x.status} for x in al]
    s = summarize(allv); s["images_with_ruler"] = n_img; s["images_scanned"] = len(paths)
    return s, measured


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs-round4")
    ap.add_argument("--run", default="r4_multires")
    ap.add_argument("--data-root", default="/Volumes/magicBLACKbox/baebugs")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--init-weights", required=True)
    ap.add_argument("--pseudo", required=True)
    ap.add_argument("--synth", required=True)
    ap.add_argument("--triage-images", nargs="+", required=True)
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--imgsz", type=int, default=800)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--sweep-images", type=int, default=120)
    a = ap.parse_args(argv)

    from .resolution import build_multires, leave_one_resolution_out, sweep
    from .train import fit, mix
    from .triage import reference_from_truth

    root, pseudo, synth = Path(a.data_root), Path(a.pseudo), Path(a.synth)
    work = root / "work" / a.run
    led = GitLedger(a.run, a.repo)
    dash = Path(a.repo) / "dashboard" / "data"; dash.mkdir(parents=True, exist_ok=True)
    real_val = pseudo / "truth_real_val.json"

    # 1 resolution sweep BEFORE multi-res training
    before = {"real": sweep(a.init_weights, real_val, work / "sweep_before_real", max_images=a.sweep_images),
              "synthetic": sweep(a.init_weights, synth / "truth_val.json", work / "sweep_before_syn",
                                 max_images=a.sweep_images)}
    before["lomo_real"] = leave_one_resolution_out(before["real"])
    (dash / f"{a.run}_sweep_before.json").write_text(json.dumps(before, indent=1))
    led.append("sweep_before", before, files={"weights": a.init_weights})

    # 2 triage: unknown vs novel (VIP) on photos, reference = database sizes
    ref_L, ref_W = reference_from_truth(pseudo / "truth_real_train.json", synth / "truth_val.json")
    alerts = root / "alerts" / f"{a.run}.jsonl"
    if alerts.exists():
        alerts.unlink()
    summ, measured = run_triage(a.init_weights, a.triage_images, ref_L, ref_W, alerts)
    (dash / f"{a.run}_triage_measured.json").write_text(json.dumps(measured))
    top = [json.loads(l) for l in alerts.read_text().splitlines()] if alerts.exists() else []
    top.sort(key=lambda r: (r["priority"] != "VIP", -r["novelty"], r["conf"]))
    (dash / f"{a.run}_alerts.json").write_text(json.dumps(top[:200], indent=1))
    led.append("triage", {**summ, "reference_n": len(ref_L)}, files={"alerts.jsonl": alerts})

    # 3 multi-resolution data (real photos at 0.3 / 1 / 3 MP + originals + synthetic)
    mr = build_multires(pseudo / "data.yaml", root / "datasets" / f"multires_{a.run}", levels=(0.3, 1.0, 3.0))
    mixed = mix([synth / "data.yaml", pseudo / "data.yaml", *mr], root / "datasets" / f"mix_{a.run}" / "data.yaml")
    led.append("multires_data", {"levels_mp": [0.3, 1.0, 3.0, "orig"], "sources": [str(m) for m in mr]},
               files={"data.yaml": mixed})

    # 4 train (per-epoch break points); multi_scale varies input size each batch
    best = fit(mixed, a.init_weights, a.epochs, imgsz=a.imgsz, batch=a.batch,
               project=str(root / "runs"), name=a.run, ledger=led, multi_scale=True)

    # 5 resolution sweep AFTER
    after = {"real": sweep(best, real_val, work / "sweep_after_real", max_images=a.sweep_images),
             "synthetic": sweep(best, synth / "truth_val.json", work / "sweep_after_syn",
                                max_images=a.sweep_images)}
    after["lomo_real"] = leave_one_resolution_out(after["real"])
    (dash / f"{a.run}_sweep_after.json").write_text(json.dumps(after, indent=1))
    led.append("sweep_after", after, files={"best.pt": best})
    print("ledger verifies:", led.verify())


if __name__ == "__main__":
    main()
