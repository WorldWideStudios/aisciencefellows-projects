"""Boxes for the bench assets in their photos, from an open-vocabulary detector (YOLOE text prompts).

These are INFERRED, not labels: each box records the model (weights sha256), the prompt list (hash), the confidence,
and the photo's tier-tree frame root (baebugs.tiers), so a person can confirm or correct it later. Confirmed boxes
become training labels for a bench/labware detector; unconfirmed ones never do.

  python -m baebugs.asset_boxes --weights yoloe-11s-seg.pt
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROMPTS = ["tube rack", "pipette tip box", "microplate", "cryovial", "conical tube", "plastic tub", "robot arm",
           "orange 3D printed shelf rack", "wooden post", "breadboard", "steel ruler", "metal frame", "vortex mixer",
           "3D printer", "printed tray frame", "hexagonal grid", "perforated metal sheet", "plastic box"]


def run(weights, conf=0.25, repo="."):
    import cv2
    from ultralytics import YOLOE

    from . import tiers as T
    m = YOLOE(weights)
    m.set_classes(PROMPTS, m.get_text_pe(PROMPTS))
    wsha = hashlib.sha256(Path(weights).read_bytes()).hexdigest()
    photos = json.loads(Path(repo, "assets/photos.json").read_text())
    out = []
    for p in photos:
        if not p.get("file"):
            continue
        img = cv2.imread(str(Path(repo, p["file"])))
        r = m.predict(img, conf=conf, verbose=False)[0]
        boxes = [{"prompt": PROMPTS[int(c)], "conf": round(float(s), 3), "bbox": [int(v) for v in b]}
                 for b, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
        fr = T.frame(img, [{"id": f"{i}:{b['prompt']}", "bbox": b["bbox"], "label": b["prompt"], "score": b["conf"]}
                           for i, b in enumerate(boxes)], meta={"photo": p["photo_id"], "source": "asset photo"})
        out.append({"photo_id": p["photo_id"], "published_sha256": p["published_sha256"], "frame_root": fr["root"],
                    "pixel_root": fr["pixel_root"], "objects_root": fr["objects_root"], "boxes": boxes})
    rec = {"status": "INFERRED (unconfirmed; not training labels)", "model": Path(weights).name, "weights_sha256": wsha,
           "prompts": PROMPTS, "prompts_sha256": hashlib.sha256(json.dumps(PROMPTS).encode()).hexdigest(), "conf_min": conf,
           "photos": out}
    Path(repo, "assets/boxes.json").write_text(json.dumps(rec, indent=1))
    return rec


def run_owl(model_id="google/owlv2-base-patch16-ensemble", conf=0.2, repo=".", out="assets/boxes_owlv2.json"):
    """Same contract with OWLv2 (Apache-2.0, Hugging Face transformers)."""
    import cv2
    import torch
    from PIL import Image
    from transformers import Owlv2ForObjectDetection, Owlv2Processor

    from . import tiers as T
    proc = Owlv2Processor.from_pretrained(model_id); m = Owlv2ForObjectDetection.from_pretrained(model_id).eval()
    photos = json.loads(Path(repo, "assets/photos.json").read_text())
    texts = [[f"a photo of a {p}" for p in PROMPTS]]
    res = []
    for p in photos:
        if not p.get("file"):
            continue
        im = Image.open(Path(repo, p["file"])).convert("RGB")
        with torch.no_grad():
            enc = proc(text=texts, images=im, return_tensors="pt"); o = m(**enc)
        side = max(im.size)                                   # OWLv2 pads to a square
        pp = getattr(proc, "post_process_object_detection", None) or proc.image_processor.post_process_object_detection
        r = pp(o, threshold=conf, target_sizes=torch.tensor([[side, side]]))[0]
        boxes = []
        for b, s, lab in zip(r["boxes"].tolist(), r["scores"].tolist(), r["labels"].tolist()):
            x0, y0, x1, y1 = (max(0, int(v)) for v in b)
            boxes.append({"prompt": PROMPTS[int(lab)], "conf": round(float(s), 3),
                          "bbox": [x0, y0, min(im.size[0], x1), min(im.size[1], y1)]})
        img = cv2.imread(str(Path(repo, p["file"])))
        fr = T.frame(img, [{"id": f"{i}:{b['prompt']}", "bbox": b["bbox"], "label": b["prompt"], "score": b["conf"]}
                           for i, b in enumerate(boxes)], meta={"photo": p["photo_id"], "source": "asset photo"})
        res.append({"photo_id": p["photo_id"], "published_sha256": p["published_sha256"], "frame_root": fr["root"],
                    "pixel_root": fr["pixel_root"], "objects_root": fr["objects_root"], "boxes": boxes})
    snap = Path(m.name_or_path)
    rec = {"status": "INFERRED (unconfirmed; not training labels)", "model": model_id,
           "weights_sha256": hashlib.sha256(json.dumps(sorted((k, list(v.shape)) for k, v in m.state_dict().items())).encode()).hexdigest(),
           "weights_note": "hash of the state-dict layout; HF revision recorded below", "revision": getattr(m.config, "_commit_hash", None),
           "prompts": PROMPTS, "prompts_sha256": hashlib.sha256(json.dumps(PROMPTS).encode()).hexdigest(), "conf_min": conf, "photos": res}
    del snap
    Path(repo, out).write_text(json.dumps(rec, indent=1))
    return rec


def image_level_eval(boxes_path, repo="."):
    """Weak check without box labels: does the detector find the KINDS of objects the asset registry says each photo shows?"""
    from .label_studio import PROMPT_TO_LABEL
    reg = json.loads(Path(repo, "kg/assets.json").read_text())["assets"]
    cat = {"rack": "rack", "tip_box": "tip_box", "plate": "plate", "tube": "tube", "tray": "tray", "insert": "insert", "arm": "arm",
           "instrument": "instrument", "container": "container", "fixture": "fixture", "stage": "stage", "electronics": "electronics",
           "reference": "reference", "tip": "tube"}
    want = {}
    for a in reg:
        for ph in a["photos"]:
            want.setdefault(ph, set()).add(cat.get(a["category"], a["category"]))
    B = json.loads(Path(repo, boxes_path).read_text())
    tp = fp = fn = 0
    for ph in B["photos"]:
        got = {PROMPT_TO_LABEL.get(b["prompt"], "container") for b in ph["boxes"]}
        w = want.get(ph["photo_id"], set())
        tp += len(got & w); fp += len(got - w); fn += len(w - got)
    p = tp / (tp + fp) if tp + fp else 0.0; r = tp / (tp + fn) if tp + fn else 0.0
    return {"boxes_file": boxes_path, "model": B["model"], "image_level_precision": round(p, 3), "image_level_recall": round(r, 3),
            "f1": round(2 * p * r / (p + r), 3) if p + r else 0.0, "tp": tp, "fp": fp, "fn": fn,
            "n_boxes": sum(len(x["boxes"]) for x in B["photos"])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--weights", default="yoloe-11s-seg.pt"); ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--owl", action="store_true"); ap.add_argument("--eval", nargs="*")
    a = ap.parse_args()
    if a.eval:
        print(json.dumps([image_level_eval(b) for b in a.eval], indent=1)); raise SystemExit(0)
    r = run_owl(conf=a.conf) if a.owl else run(a.weights, a.conf)
    print(json.dumps({x["photo_id"]: len(x["boxes"]) for x in r["photos"]}))
