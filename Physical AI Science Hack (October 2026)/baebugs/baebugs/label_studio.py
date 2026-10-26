"""Confirm detector boxes in Label Studio (open source, Apache-2.0) and bring the human labels back with custody.

  export:  assets/boxes*.json (INFERRED) -> assets/label_studio/{config.xml, tasks.json}
           tasks carry the detector boxes as Label Studio *predictions* (pre-annotations), images by public GitHub URL
  run:     pip install label-studio && label-studio start
           create a project, paste config.xml as the labeling interface, import tasks.json, fix/confirm boxes, export JSON
  import:  python -m baebugs.label_studio import export.json
           -> assets/labels_confirmed.json: only human *annotations* become labels (never predictions), each with the
              annotator id, time, image sha256, and a hash; appended to daisy/assets_mmr.jsonl

  python -m baebugs.label_studio export [--boxes assets/boxes.json]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/biobitworks/baebugs/main/"
LABELS = ["rack", "tip_box", "plate", "tube", "tray", "insert", "arm", "instrument", "container", "fixture", "stage",
          "electronics", "reference"]
PROMPT_TO_LABEL = {
    "tube rack": "rack", "pipette tip box": "tip_box", "microplate": "plate", "cryovial": "tube", "conical tube": "tube",
    "plastic tub": "container", "robot arm": "arm", "orange 3D printed shelf rack": "rack", "wooden post": "fixture",
    "breadboard": "electronics", "steel ruler": "reference", "metal frame": "fixture", "vortex mixer": "instrument",
    "3D printer": "instrument", "printed tray frame": "tray", "hexagonal grid": "insert", "perforated metal sheet": "insert",
    "plastic box": "container",
}


def config_xml():
    labels = "\n".join(f'    <Label value="{x}"/>' for x in LABELS)
    return f'<View>\n  <Image name="image" value="$image"/>\n  <RectangleLabels name="label" toName="image">\n{labels}\n  </RectangleLabels>\n</View>\n'


def export(boxes_path="assets/boxes.json", out="assets/label_studio", repo="."):
    B = json.loads(Path(repo, boxes_path).read_text())
    photos = {p["photo_id"]: p for p in json.loads(Path(repo, "assets/photos.json").read_text())}
    tasks = []
    for ph in B["photos"]:
        p = photos[ph["photo_id"]]
        W, Hh = p["size_px"]
        res = []
        for i, b in enumerate(ph["boxes"]):
            x0, y0, x1, y1 = b["bbox"]
            res.append({"id": f"{ph['photo_id']}_{i}", "type": "rectanglelabels", "from_name": "label", "to_name": "image",
                        "original_width": W, "original_height": Hh, "image_rotation": 0,
                        "value": {"rotation": 0, "x": 100 * x0 / W, "y": 100 * y0 / Hh, "width": 100 * (x1 - x0) / W,
                                  "height": 100 * (y1 - y0) / Hh, "rectanglelabels": [PROMPT_TO_LABEL.get(b["prompt"], "container")]},
                        "meta": {"text": [f"detector said '{b['prompt']}' conf {b['conf']}"]}})
        tasks.append({"data": {"image": RAW + p["file"], "photo_id": ph["photo_id"], "published_sha256": p["published_sha256"],
                               "frame_root": ph["frame_root"]},
                      "predictions": [{"model_version": f"{B['model']}:{B['weights_sha256'][:12]}", "score": 0.0, "result": res}]})
    o = Path(repo, out); o.mkdir(parents=True, exist_ok=True)
    (o / "config.xml").write_text(config_xml())
    (o / "tasks.json").write_text(json.dumps(tasks, indent=1))
    return {"tasks": len(tasks), "boxes": sum(len(t["predictions"][0]["result"]) for t in tasks)}


def import_confirmed(export_path, out="assets/labels_confirmed.json", repo="."):
    from .mmr import MMRLog
    exp = json.loads(Path(export_path).read_text())
    labels = []
    for t in exp:
        for ann in t.get("annotations", []):                      # human work only; predictions are ignored
            if ann.get("was_cancelled"):
                continue
            for r in ann.get("result", []):
                if r.get("type") != "rectanglelabels":
                    continue
                v = r["value"]; W, Hh = r["original_width"], r["original_height"]
                labels.append({"photo_id": t["data"].get("photo_id"), "published_sha256": t["data"].get("published_sha256"),
                               "label": v["rectanglelabels"][0],
                               "bbox": [round(v["x"] * W / 100), round(v["y"] * Hh / 100),
                                        round((v["x"] + v["width"]) * W / 100), round((v["y"] + v["height"]) * Hh / 100)],
                               "annotator": ann.get("completed_by"), "time": ann.get("updated_at") or ann.get("created_at")})
    rec = {"type": "confirmed_labels", "n": len(labels),
           "sha256": hashlib.sha256(json.dumps(labels, sort_keys=True).encode()).hexdigest(), "source": Path(export_path).name}
    Path(repo, out).write_text(json.dumps({**rec, "labels": labels}, indent=1))
    MMRLog(Path(repo, "daisy/assets_mmr.jsonl")).append(rec)
    return rec


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "import":
        print(json.dumps(import_confirmed(a[1])))
    else:
        bp = a[a.index("--boxes") + 1] if "--boxes" in a else "assets/boxes.json"
        print(json.dumps(export(bp)))
