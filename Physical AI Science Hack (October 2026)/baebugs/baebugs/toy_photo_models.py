"""How each model sees real photos of the printed PA12 toys (first real-photo check of the toy lane).

Per photo: YOLOE (text prompt), OWLv2 (text prompt) detect toys; the DAISY-004 ORDER classifier labels each OWLv2 crop;
the local VLM describes the whole photo. Outputs are INFERRED and recorded with model ids and the photo's frame root.

  python -m baebugs.toy_photo_models --photos assets/photos/pa12_toys_two_on_floor.jpg assets/photos/pa12_toys_box.jpg \
      --order /Volumes/magicBLACKbox/baebugs/daisy/local/004_v4/ORDER_best.pt --out docs/toy_photo_models
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROMPTS = ["toy insect", "insect", "beetle", "fly", "bee"]


def run(photos, order_w, out, yoloe_w="yoloe-11s-seg.pt", vlm="qwen2.5vl:3b", conf=0.15):
    import cv2
    import torch
    from PIL import Image
    from transformers import Owlv2ForObjectDetection, Owlv2Processor
    from ultralytics import YOLO, YOLOE

    from . import local_vlm
    from . import tiers as T
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    ye = YOLOE(yoloe_w); ye.set_classes(PROMPTS, ye.get_text_pe(PROMPTS))
    proc = Owlv2Processor.from_pretrained("google/owlv2-base-patch16-ensemble")
    owl = Owlv2ForObjectDetection.from_pretrained("google/owlv2-base-patch16-ensemble").eval()
    cls = YOLO(order_w)
    res = {"models": {"yoloe": yoloe_w, "owlv2": "google/owlv2-base-patch16-ensemble",
                      "order": {"file": Path(order_w).name, "sha256": hashlib.sha256(Path(order_w).read_bytes()).hexdigest()},
                      "vlm": vlm}, "prompts": PROMPTS, "photos": []}
    for ph in photos:
        img = cv2.imread(str(ph)); H, W = img.shape[:2]
        r = ye.predict(img, conf=conf, verbose=False)[0]
        yb = [{"label": PROMPTS[int(c)], "conf": round(float(s), 3), "bbox": [int(v) for v in b]}
              for b, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
        im = Image.open(ph).convert("RGB")
        with torch.no_grad():
            o = owl(**proc(text=[[f"a photo of a {p}" for p in PROMPTS]], images=im, return_tensors="pt"))
        pp = getattr(proc, "post_process_object_detection", None) or proc.image_processor.post_process_object_detection
        rr = pp(o, threshold=conf, target_sizes=torch.tensor([[max(W, H), max(W, H)]]))[0]
        ob = sorted(({"label": PROMPTS[int(l)], "conf": round(float(s), 3), "bbox": [max(0, int(v)) for v in b]}
                     for b, s, l in zip(rr["boxes"].tolist(), rr["scores"].tolist(), rr["labels"].tolist())),
                    key=lambda x: -x["conf"])
        # keep distinct objects (greedy NMS at IoU 0.5) and classify each crop with the ORDER router
        keep = []
        for b in ob:
            if all(_iou(b["bbox"], k["bbox"]) < 0.5 for k in keep):
                keep.append(b)
        for b in keep[:12]:
            x0, y0, x1, y1 = b["bbox"]; crop = img[y0:min(H, y1), x0:min(W, x1)]
            if crop.size:
                c = cls.predict(crop, imgsz=224, verbose=False)[0]
                b["order"] = {"label": c.names[int(c.probs.top1)], "conf": round(float(c.probs.top1conf), 3)}
        vl = local_vlm.chat_json("These are 3D-printed toy insects. How many toys do you see, and which insect order does each look like? "
                                 'Reply JSON: {"count": n, "toys": [{"order": "...", "confidence": 0-1}]}', img, model=vlm) \
            if local_vlm.available(vlm) else {"unavailable": True}
        fr = T.frame(img, [{"id": f"owl{i}", "bbox": b["bbox"], "label": b.get("order", {}).get("label")} for i, b in enumerate(keep[:12])],
                     meta={"photo": Path(ph).name, "source": "toy photo models"})
        vis = img.copy()
        for b in yb:
            cv2.rectangle(vis, tuple(b["bbox"][:2]), tuple(b["bbox"][2:]), (0, 200, 255), 4)
        for b in keep[:12]:
            cv2.rectangle(vis, tuple(b["bbox"][:2]), tuple(b["bbox"][2:]), (255, 80, 40), 4)
            t = f"{b.get('order', {}).get('label', '?')} {b.get('order', {}).get('conf', 0):.2f}"
            cv2.putText(vis, t, (b["bbox"][0], max(30, b["bbox"][1] - 10)), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 80, 40), 4)
        cv2.imwrite(str(out / f"{Path(ph).stem}_models.jpg"), cv2.resize(vis, (W // 2, H // 2)), [cv2.IMWRITE_JPEG_QUALITY, 80])
        res["photos"].append({"photo": Path(ph).name, "sha256": hashlib.sha256(Path(ph).read_bytes()).hexdigest(), "frame_root": fr["root"],
                              "yoloe": yb, "owlv2": keep[:12], "owlv2_raw_n": len(ob), "vlm": vl})
    (out / "results.json").write_text(json.dumps(res, indent=1))
    return res


def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u else 0.0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--photos", nargs="+"); ap.add_argument("--order"); ap.add_argument("--out")
    a = ap.parse_args()
    r = run(a.photos, a.order, a.out)
    for p in r["photos"]:
        print(p["photo"], "YOLOE", len(p["yoloe"]), "OWLv2", len(p["owlv2"]), [b.get("order") for b in p["owlv2"]][:6], "VLM", p["vlm"])
