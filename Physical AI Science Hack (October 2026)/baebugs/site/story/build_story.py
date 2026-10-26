"""Build site/story/index.html: the end-to-end BaeBugs flow, every number read from repo files.

Each step lists the files it reads with their sha256 (computed from the bytes, so every hash resolves).
Material that lives only in an open, unmerged PR is labelled as such and carries no hash.

  python site/story/build_story.py
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def src(path):
    p = ROOT / path
    return {"path": path, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}


def load(path):
    return json.loads((ROOT / path).read_text())


def build(output_path: Path | None = None):
    filters = load("print/filters/filters.json")
    passage = load("print/filters/passage/body_folded/summary.json")
    mvp = load("site/mvp/mvp.json")
    daisy = load("daisy/results/DAISY-BB-004/v4/results.json")
    crops = load("daisy/taxon_crops_report.json")
    toyphoto = load("docs/toy_photo_models/results.json")
    toys = list(csv.DictReader((ROOT / "print/fuse1/manifest.csv").open()))

    by_real = collections.Counter(f["realisation"] for f in filters)
    filt_rows = [{"id": f["id"], "shape": f["shape"], "realisation": f["realisation"],
                  "inscribed_d_mm": f.get("inscribed_d_mm"), "open_area": f.get("open_area"),
                  "material": f["materials"][0], "printable": f.get("fuse_printable", False)}
                 for f in filters]
    holes = passage["holes"]
    pas = [{"id": k, "shape": v["shape"], "d": v["inscribed_d_mm"], "flat": v["pass_flat"],
            "tumbled": v["pass_tumbled"], "end_on": v["end_on_only"], "retained": v["retained"]}
           for k, v in holes.items()]

    o = daisy["results"]["ORDER"]
    fam = {k: {"verdict": v.get("verdict"), "val_f1": v.get("eval", {}).get("val", {}).get("macro_f1"),
               "test_f1": (v.get("eval", {}).get("test") or {}).get("macro_f1")}
           for k, v in daisy["results"].items() if k != "ORDER"}

    photos = [{"photo": p["photo"], "sha256": p["sha256"], "frame_root": p["frame_root"],
               "yoloe": len(p["yoloe"]),
               "owlv2": [{"label": d["label"], "conf": d["conf"], "order": d.get("order")} for d in p["owlv2"]],
               "vlm_count": (p.get("vlm") or {}).get("count")} for p in toyphoto["photos"]]

    lengths = [float(t["length_mm"]) for t in toys if t["length_mm"]]
    remixes = mvp["remixes"]
    cust = mvp["custody"]

    data = {
        "root": mvp["root"], "roots": mvp["roots"], "repo": mvp["repo"],
        "filters": {"n": len(filters), "by_realisation": by_real, "rows": filt_rows,
                    "stl": len(list((ROOT / "print/filters/stl").glob("*.stl"))),
                    "scad": len(list((ROOT / "print/filters/scad").glob("*.scad"))),
                    "passage": pas, "toys_tested": 91},
        "vision": {"models": toyphoto["models"], "prompts": toyphoto["prompts"], "photos": photos},
        "models": {"crops": crops["crops"], "by_split": crops["by_split"], "leakage": crops["leakage_media_ids"],
                   "order": {"classes": o["classes"], "val": o["eval"]["val"], "test": o["eval"]["test"],
                             "verdict": o["verdict"], "weights_sha256": o["weights_sha256"]},
                   "families": fam, "protocol_sha256": daisy["protocol_sha256"]},
        "toys": {"n": len(toys), "orders": collections.Counter(t["order"] for t in toys).most_common(),
                 "plans": len({t["plan"] for t in toys}), "len_min": min(lengths), "len_max": max(lengths),
                 "roles": collections.Counter(t["training_role"] for t in toys),
                 "scad": len(list((ROOT / "print/fuse1/scad").glob("*.scad")))},
        "remix": {"items": [{k: r[k] for k in ("id", "name", "material", "grams", "usd", "licence", "leaf", "bbox_mm")}
                            for r in remixes],
                  "grams": round(sum(r["grams"] for r in remixes), 1),
                  "usd": round(sum(r["usd"] for r in remixes), 2)},
        "custody": {"rule": cust["rule"], "breaks": cust["breaks"], "result_breaks": cust["result_breaks"],
                    "photo_breaks": cust["withheld_photo_breaks"], "leaves": len(mvp["leaves"]),
                    "mmr": sorted(mvp["mmr"])},
        "sources": {
            "filters": [src("print/filters/filters.json"), src("print/filters/passage/body_folded/summary.json"),
                        src("print/filters/scad/filter_plate.scad"), src("baebugs/punch_filters.py"),
                        src("baebugs/passage_twin.py")],
            "robot": [src("baebugs/variable_aperture.py"), src("print/filters/variable_aperture/slot_pair.scad"),
                      src("print/filters/variable_aperture/demo_run_slot.json"),
                      src("filtration-robot/README.md"), src("filtration-robot/vision/filter_plan.py"),
                      src("docs/workflow_video/README.md"),
                      src("docs/sieving_robot/sieving_demo.mp4"), src("docs/sieving_robot/README.md")],
            "vision": [src("docs/toy_photo_models/results.json"), src("baebugs/camera.py"),
                       src("baebugs/toy_photo_models.py"), src("baebugs/local_vlm.py")],
            "models": [src("daisy/results/DAISY-BB-004/v4/results.json"), src("daisy/taxon_crops_report.json"),
                       src("daisy/DAISY-BB-004-prereg.md"), src("baebugs/taxon_crops.py"), src("baebugs/train.py")],
            "toys": [src("print/fuse1/manifest.csv"), src("print/fuse1/README.md"), src("baebugs/scad_export.py")],
            "remix": [src("print/labware/README.md"), src("print/labware/scad/labware.scad"),
                      src("print/labware/merkle/lab_root.json")],
            "custody": [src("site/mvp/mvp.json"), src("kg/aok.json")],
        },
    }
    html = (HERE / "template.html").read_text().replace("/*STORY_DATA*/null", json.dumps(data, sort_keys=True))
    destination = HERE / "index.html" if output_path is None else Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html)
    print("wrote", destination, len(html), "bytes")


if __name__ == "__main__":
    build()
