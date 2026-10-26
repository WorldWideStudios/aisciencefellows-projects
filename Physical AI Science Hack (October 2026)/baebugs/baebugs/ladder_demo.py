"""Escalation-ladder demo on the printed toys (no real insects at the bench), with real deciders where they exist.

Per toy: three steps, each a snapshot frame built with baebugs.tiers and judged by the ladder.
  sort   the toy on a tray canvas (filter = its kit tray, protocol P-sieve-v1)
  image  close-up at 20 px/mm (protocol P-image-v1)
  pick   the same tray after the arm took it: the frame diff must show exactly one break box where the toy
         was, and the toy's object must be gone; otherwise the pick is REWORK
Rungs: FAMILY_Hymenoptera (California only, NULL out of state) -> ORDER router (DAISY-BB-004 v4 weights) ->
local VLM (Ollama qwen2.5vl:3b) -> Claude (only if ANTHROPIC_API_KEY is set; otherwise it reports
UNAVAILABLE and escalates) -> human (nobody at the bench: HOLD, queued for the entomologist).

  python -m baebugs.ladder_demo --out /Volumes/magicBLACKbox/baebugs/ladder/demo --weights /Volumes/magicBLACKbox/baebugs/daisy/local/004_v4
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np

from . import ladder as L
from . import tiers as T
from .mmr import MMRLog

BG = (196, 202, 206)


def tensor_or_file_sha(p):
    try:
        from .weights_id import tensor_sha256
        return "tensor:" + tensor_sha256(p)
    except Exception:  # noqa: BLE001
        return "file:" + hashlib.sha256(Path(p).read_bytes()).hexdigest()


def toys(kg="print/fuse1/kg", n_ca=6, n_out=4, n_tiny=2):
    idx = sorted(json.loads(Path(kg, "index.json").read_text()), key=lambda x: x["name"])
    pick = lambda g, n: [x for x in idx if x["group"] == g][:: max(1, len([x for x in idx if x["group"] == g]) // n)][:n]
    return pick("california", n_ca) + pick("novel_outside_ca", n_out) + pick("fill_in_1-3mm", n_tiny), idx


def mask_bbox(img, bg=BG, tol=12):
    m = (np.abs(img.astype(int) - np.array(bg)).sum(2) > tol).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return None, None
    c = max(cs, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)
    return [x, y, x + w, y + h], c.reshape(-1, 2)


def tray(render, H=360, W=480, at=(60, 80)):
    canvas = np.zeros((H, W, 3), np.uint8); canvas[:] = BG
    r = render[: H - at[1], : W - at[0]]
    canvas[at[1]:at[1] + r.shape[0], at[0]:at[0] + r.shape[1]] = r
    return canvas


def yolo_rung(name, weights, scope, threshold):
    from ultralytics import YOLO
    m = YOLO(str(weights))

    def decide(ctx):
        x0, y0, x1, y1 = ctx["object"]["bbox"]
        crop = ctx["image"][y0:y1, x0:x1]
        r = m.predict(crop, imgsz=224, verbose=False)[0]
        conf = float(r.probs.top1conf); lab = r.names[int(r.probs.top1)]
        return {"outcome": "APPROVE", "confidence": conf, "label": lab}
    return L.Rung(name, tensor_or_file_sha(weights), decide, threshold=threshold, novelty_ceiling=0.9, scope=scope)


def vlm_rung(model="qwen2.5vl:3b"):
    from . import local_vlm

    def decide(ctx):
        if not local_vlm.available(model):
            return {"outcome": "UNAVAILABLE", "confidence": 0.0}
        x0, y0, x1, y1 = ctx["object"]["bbox"]
        crop = ctx["image"][max(0, y0 - 10):y1 + 10, max(0, x0 - 10):x1 + 10]
        prompt = (f"This is a photo of a printed toy insect at the '{ctx['step']}' step of a sample-prep line. "
                  "Is a single intact insect-like object visible and fit to move to the next step? "
                  'Reply JSON only: {"outcome": "APPROVE" or "REWORK" or "HOLD", "confidence": 0-1, "label": insect order guess}')
        out = local_vlm.chat_json(prompt, crop, model=model)
        try:
            out["confidence"] = float(out.get("confidence", 0))
        except (TypeError, ValueError):
            out["confidence"] = 0.0
        if out.get("outcome") not in L.OUTCOMES:
            out = {"outcome": "UNAVAILABLE", "confidence": 0.0, "raw": out}
        return out
    return L.Rung(f"local:{model}", f"ollama:{model}", decide, threshold=0.8, novelty_ceiling=0.99)


def frontier_rung():
    def decide(ctx):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return {"outcome": "UNAVAILABLE", "confidence": 0.0, "why": "no API key on this machine"}
        from .claude_review import review
        r = review(ctx["image"], [])
        ok = not r.get("issues") if isinstance(r, dict) else False
        return {"outcome": "APPROVE" if ok else "HOLD", "confidence": 0.85, "review": r}
    return L.Rung("frontier:claude", "anthropic:claude", decide, threshold=0.8)


def human_rung():
    return L.Rung("human", "entomologist", lambda ctx: {"outcome": "HOLD", "confidence": 1.0,
                                                        "label": "queued for the entomologist (nobody at the bench)"})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--weights", required=True)
    ap.add_argument("--ppm", type=float, default=20.0); ap.add_argument("--vlm", default="qwen2.5vl:3b")
    a = ap.parse_args(argv)
    from .model_compare import render
    from .novelty import novel_sizes
    out = Path(a.out); (out / "snapshots").mkdir(parents=True, exist_ok=True)
    chain = out / "ladder_mmr.jsonl"
    if chain.exists():
        chain.unlink()
    log = MMRLog(chain)
    sel, idx = toys()
    ca = [x for x in idx if x["group"] == "california"]
    nov = {r["i"]: r["novelty"] for r in novel_sizes([x["length_mm"] for x in sel], [x["body_width_mm"] for x in sel],
                                                       [x["length_mm"] for x in ca], [x["body_width_mm"] for x in ca])}
    w = Path(a.weights)
    ladder = [yolo_rung("taxon:FAMILY_Hymenoptera", w / "FAMILY_Hymenoptera_best.pt", {"orders": ["Hymenoptera"], "states": ["CA"]}, 0.9),
              yolo_rung("taxon:ORDER", w / "ORDER_best.pt", {}, 0.9),
              vlm_rung(a.vlm), frontier_rung(), human_rung()]
    rows = []
    for i, x in enumerate(sel):
        state = "CA" if x["group"] == "california" else "OUT"
        r20 = render(x["length_mm"], x["plan"], a.ppm)
        on = tray(r20)
        bb_on, cont_on = mask_bbox(on)
        off = on.copy()                                   # the arm takes the toy: only its pixels change
        m = np.zeros(on.shape[:2], np.uint8)
        cv2.drawContours(m, [cont_on.reshape(-1, 1, 2).astype(np.int32)], -1, 1, thickness=-1)
        m = cv2.dilate(m, np.ones((5, 5), np.uint8))
        off[m.astype(bool)] = BG
        frames = {}
        for step, img, proto in (("sort", on, "P-sieve-v1"), ("image", r20, "P-image-v1"), ("pick", off, "P-pick-v1")):
            bb, _cont = mask_bbox(img)
            objs = [{"id": x["name"], "bbox": bb, "label": x["order"]}] if bb else []
            fr = T.frame(img, objs, meta={"step": step, "specimen": x["name"], "protocol": proto})
            frames[step] = (img, fr)
        d_pick = T.diff(frames["sort"][1], frames["pick"][1])
        for step in ("sort", "image", "pick"):
            img, fr = frames[step]
            obj = fr["objects"][0] if fr["objects"] else {"hash": T._h("no object"), "bbox": d_pick["break_boxes"][0] if d_pick["break_boxes"] else [0, 0, 1, 1]}
            ctx = {"order": x["order"], "family": x["family"], "state": state, "novelty": nov[i], "filter": x["kit_tray"],
                   "protocol": fr["meta"]["protocol"], "module": "bench", "step": step, "image": img}
            if step == "pick":
                bx = d_pick["break_boxes"]
                ok = (len(bx) == 1 and not fr["objects"] and bx[0][0] <= bb_on[0] and bx[0][1] <= bb_on[1]
                      and bx[0][2] >= bb_on[2] and bx[0][3] >= bb_on[3]
                      and (bx[0][2] - bx[0][0]) * (bx[0][3] - bx[0][1]) <= 4 * max(1, (bb_on[2] - bb_on[0] + 32) * (bb_on[3] - bb_on[1] + 32)))
                ladder_pick = [L.Rung("check:frame-diff", "baebugs.tiers.diff", lambda c, ok=ok: {"outcome": "APPROVE" if ok else "REWORK",
                                                                                                    "confidence": 1.0, "label": "pick verified: one break box around where the toy was" if ok else "diff does not match the pick"}),
                               human_rung()]
                row, dec = L.record_step(log, x["name"], step, T.summary(fr), obj, ctx, ladder_pick)
            else:
                row, dec = L.record_step(log, x["name"], step, T.summary(fr), obj, ctx, ladder)
            snap = T.draw(img, fr, d_pick if step == "pick" else None, tiers=(1, 3))
            cv2.imwrite(str(out / "snapshots" / f"{i:02d}_{step}.png"), snap)
            rows.append({"toy": x["name"], "group": x["group"], "truth_order": x["order"], "step": step, **dec,
                         "novelty": round(nov[i], 3), "frame_root": fr["root"], "leaf": row["leaf"]})
            if dec["outcome"] != "APPROVE":
                break
    stats = L.markov(log.records)
    (out / "markov.json").write_text(json.dumps(stats, indent=1))
    (out / "rows.json").write_text(json.dumps(rows, indent=1))
    print(json.dumps({"chain_root": log.records[-1]["root"], "records": len(log.records), "stats_sha256": stats["stats_sha256"],
                      "decided_by": stats["decided_by"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
