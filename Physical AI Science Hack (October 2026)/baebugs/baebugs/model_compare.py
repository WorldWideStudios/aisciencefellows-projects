"""Model comparison on the TOY insect datasets: qwen / lfm (text), qwen2.5-VL
(image), YOLO / YOLOE / classical (vision measurement) vs the deterministic
logic tier. Every answer is scored the same way: rebuild the proposed insect,
compare its insect hash (Merkle KG) with the held-out one.

Inputs per held-out toy
  text   : the numeric camera observation (envelope 0.1 mm, top area, counts)
           + context records (insect_lomo.context_text)
  image  : a top-down orthographic render at a known px/mm (5 / 10 / 20 px/mm,
           the megapixel axis). Vision measurers return length / width / area
           of the largest detection; the twin then reconstructs (plan, length)
           from that top view only (no height, no appendage counts).
           qwen2.5-VL reads the image + scale + family table directly.

  python -m baebugs.model_compare text --models qwen3:1.7b,lfm2.5-1.2b-instruct:q4_k_m --ledger
  python -m baebugs.model_compare vision --methods yolo,yoloe,classical,vlm:qwen2.5vl:3b --ppm 5,10,20 --ledger
  python -m baebugs.model_compare table
"""
from __future__ import annotations

import base64
import csv
import json
import time
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from . import insect_lomo as IL
from .insect_kg import insect_tree

KG = "print/fuse1/kg"
OUT = "print/fuse1/kg/compare"
STUDENT = "/Volumes/magicBLACKbox/baebugs/runs/r3_real/weights/best.pt"


# ------------------------------------------------------------------- render

def render(length_mm, plan, ppm, margin_mm=4.0, bg=(196, 202, 206), color=(118, 118, 124), seed=0):
    """Top-down orthographic render (painter's algorithm, Lambert shading) of
    the toy at exactly ppm px/mm, body axis along x. Returns BGR uint8."""
    _, root = insect_tree(length_mm, plan)
    m = root["_mesh"]
    v = m.vertices.copy()
    lo, hi = v.min(0), v.max(0)
    W = int(np.ceil((hi[0] - lo[0] + 2 * margin_mm) * ppm)); H = int(np.ceil((hi[1] - lo[1] + 2 * margin_mm) * ppm))
    img = np.zeros((H, W, 3), np.uint8); img[:] = bg
    px = np.stack([(v[:, 0] - lo[0] + margin_mm) * ppm, (hi[1] - v[:, 1] + margin_mm) * ppm], 1)
    f = m.faces
    order = np.argsort(v[f].mean(1)[:, 2])                 # low z first
    n = m.face_normals
    light = np.array([0.3, -0.3, 0.9]); light /= np.linalg.norm(light)
    for i in order:
        if n[i, 2] <= 0:
            continue
        s = 0.35 + 0.65 * max(0.0, float(n[i] @ light))
        cv2.fillConvexPoly(img, np.round(px[f[i]] * 16).astype(np.int32),
                           tuple(int(c * s) for c in color), lineType=cv2.LINE_AA, shift=4)
    rng = np.random.default_rng(seed)
    img = np.clip(img.astype(np.int16) + rng.normal(0, 3, img.shape).astype(np.int16), 0, 255).astype(np.uint8)
    return cv2.GaussianBlur(img, (3, 3), 0)


# ------------------------------------------------------------- vision tiers

_yolo = {}


def measure(method, img, ppm):
    """Largest detection -> {length_mm, width_mm, area_mm2, conf, n_dets} or None."""
    from .measure import YoloMeasurer, classical_measure
    if method == "yolo":
        if "yolo" not in _yolo:
            _yolo["yolo"] = YoloMeasurer(STUDENT, conf=0.15)
        ms = _yolo["yolo"](img, ppm)
    elif method == "yoloe":
        from .specimen_photo import segment_yoloe
        _, ms = segment_yoloe(img, ppm, conf=0.15, length_range=(0.3, 60))
    elif method == "classical":
        ms = classical_measure(img, ppm)
    else:
        raise ValueError(method)
    if not ms:
        return None
    b = max(ms, key=lambda m: m.area_mm2)
    return {"length_mm": round(b.length_mm, 2), "width_mm": round(b.width_mm, 2), "area_mm2": round(b.area_mm2, 1),
            "conf": round(float(b.conf), 3), "n_dets": len(ms)}


def solve_topview(meas, ctx, k=8):
    """Twin reconstruction from a top view only: match (length, width) to the
    envelope x, y of every (plan, length) candidate, then area among the best k."""
    if meas is None:
        return {"plan": None, "length_mm": None, "family": None, "novel": True, "reason": "no detection"}
    tab = IL.twin_table()
    ml, mw = max(meas["length_mm"], meas["width_mm"]), min(meas["length_mm"], meas["width_mm"])
    # orientation-free: the long side may be the leg span, not the body axis
    scored = sorted(((abs(max(env[0], env[1]) - ml) + abs(min(env[0], env[1]) - mw), plan, L)
                     for plan, L, env, c in tab), key=lambda t: t[0])[:k]
    best = min(scored, key=lambda t: t[0] + 0.02 * abs(IL.rebuild_observation(t[2], t[1])[0]["top_area_mm2"] - meas["area_mm2"]))
    _, plan, L = best
    fams = IL.family_stats(ctx)
    cands = [f for f in fams.values() if plan in f["plans"]]
    score = lambda f: abs(L - f["mean"]) / f["sd"] if f.get("mean") is not None else 2.05 + min(abs(L - l) for l in f["lengths"]) / 2
    fam = min(cands, key=score)["family"] if cands else None
    nov, why = IL.novelty_logic(fam, L, fams)
    return {"plan": plan, "length_mm": L, "family": fam, "novel": nov, "reason": f"top-view twin; {why}",
            "tied_plans": sorted({p for e, p, l in scored if e <= scored[0][0] + 1e-9})}


def ask_vlm(model, img, ppm, ctx, host="http://localhost:11434", timeout=240):
    _ok, buf = cv2.imencode(".png", img)
    fams = IL.family_stats(ctx)
    table = "\n".join(f"{f['family']} | {','.join(f['plans'])} | " +
                      (f"{f['mean']}±{f['sd']}" if f.get("mean") is not None else f"seen {f['lengths']}")
                      for f in sorted(fams.values(), key=lambda e: e["family"]))
    prompt = (IL.SYSTEM.format(plans=", ".join(IL.PLAN_LIST)) +
              f"\n\nThe image is a top-down view at exactly {ppm} px per mm (image {img.shape[1]}x{img.shape[0]} px). "
              f"The body axis is horizontal.\nFAMILIES (family | plans | mean±SD mm):\n{table}\n\nReconstruct this insect.")
    body = {"model": model, "stream": False, "format": "json", "options": {"temperature": 0, "seed": 0, "num_predict": 400},
            "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(buf.tobytes()).decode()]}]}
    t = time.time()
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(
            f"{host}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}),
            timeout=timeout).read())
        txt = r["message"]["content"]
    except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
        return None, f"error {e}", time.time() - t
    return IL._parse_json(txt), txt[:300], time.time() - t


# ------------------------------------------------------------------ runners

def _ledger(on, repo="."):
    if not on:
        return None
    from .git_ledger import GitLedger
    return GitLedger("model_compare", repo)


def run_text(models, protocols, kg=KG, out=OUT, ledger=None, limit=None):
    res = {}
    for model in models:
        d = Path(out) / "text" / model.replace(":", "_").replace("/", "_")
        t = time.time()
        s = IL.run(kg, d, protocols, local=model, ledger=None, limit=limit)
        res[model] = s
        print(f"[text] {model} done in {time.time() - t:.0f}s", flush=True)
        if ledger is not None:
            ledger.append(f"text_{model}", {p: s[p].get("local") for p in s}, files={"summary": d / "summary.json"})
    return res


def run_vision(methods, ppms, kg=KG, out=OUT, ledger=None, limit=None, render_dir=None):
    index = IL.load_index(kg)
    IL.twin_table()
    rdir = Path(render_dir or Path(out) / "renders")
    for ppm in ppms:
        (rdir / f"ppm{ppm:g}").mkdir(parents=True, exist_ok=True)
    for method in methods:
        for ppm in ppms:
            recs = []
            t0 = time.time()
            for i, (held, ctx, _) in enumerate(IL.cases(index, "lomo")):
                if limit and i >= limit:
                    break
                fp = rdir / f"ppm{ppm:g}" / f"{held['name']}.png"
                if fp.exists():
                    img = cv2.imread(str(fp))
                else:
                    img = render(held["length_mm"], held["plan"], ppm); cv2.imwrite(str(fp), img)
                r = {"method": method, "ppm": ppm, "held": held["name"], "training_role": held.get("training_role", ""),
                     "group": held["group"], "length_mm": held["length_mm"], "plan": held["plan"]}
                if method.startswith("vlm:"):
                    ans, raw, dt = ask_vlm(method[4:], img, ppm, ctx)
                    r["tier"] = {**IL.check(ans or {}, held, ctx), "seconds": round(dt, 1), "raw": raw}
                else:
                    meas = measure(method, img, ppm)
                    o = held["observation"]
                    r["measurement"] = meas
                    if meas:
                        r["meas_err_mm"] = {"length": round(meas["length_mm"] - max(o["envelope_mm"][:2]), 2),
                                            "width": round(meas["width_mm"] - min(o["envelope_mm"][:2]), 2),
                                            "area": round(meas["area_mm2"] - o["top_area_mm2"], 1)}
                    r["tier"] = IL.check(solve_topview(meas, ctx), held, ctx)
                recs.append(r)
                if i % 10 == 0:
                    print(f"[vision] {method} ppm{ppm:g} {i}/{len(index)} {time.time() - t0:.0f}s", flush=True)
            d = Path(out) / "vision"; d.mkdir(parents=True, exist_ok=True)
            fn = d / f"{method.replace(':', '_')}_ppm{ppm:g}.jsonl"
            fn.write_text("".join(json.dumps(r, default=IL._np) + "\n" for r in recs))
            s = vision_summary(recs)
            print(f"[vision] {method} ppm{ppm:g}: {s}", flush=True)
            if ledger is not None:
                ledger.append(f"vision_{method}_ppm{ppm:g}", s, files={"results": fn})


def vision_summary(recs):
    t = [r["tier"] for r in recs]
    neg = [r for r in recs if r["training_role"].startswith("edge_negative")]
    errs = [abs(r["meas_err_mm"]["length"]) for r in recs if r.get("meas_err_mm")]
    return {"n": len(recs), "detected": sum(bool(r.get("measurement")) or "measurement" not in r for r in recs),
            "exact_hash": sum(x["hash_match"] for x in t), "topology_ok": sum(bool(x.get("topo_match")) for x in t),
            "tray_ok": sum(bool(x.get("tray_match")) for x in t), "triage_ok": sum(bool(x.get("triage_ok")) for x in t),
            "edge_negatives": len(neg), "edge_negatives_rejected": sum(bool(r["tier"].get("novel_logic")) for r in neg),
            "median_abs_len_err_mm": round(float(np.median([abs(x["length_err_mm"]) for x in t if "length_err_mm" in x])), 2)
            if any("length_err_mm" in x for x in t) else None,
            "median_abs_meas_err_mm": round(float(np.median(errs)), 2) if errs else None}


def table(out=OUT, logic_dir="print/fuse1/kg/lomo"):
    """One CSV: model x input x protocol."""
    rows = []
    ls = json.loads((Path(logic_dir) / "summary.json").read_text())
    for p, s in ls.items():
        rows.append({"model": "logic (twin search)", "input": "text obs", "protocol": p, **_pick(s["logic"])})
    for d in sorted((Path(out) / "text").glob("*/summary.json")):
        s = json.loads(d.read_text())
        for p, b in s.items():
            if "local" in b:
                rows.append({"model": d.parent.name, "input": "text obs", "protocol": p, **_pick(b["local"])})
    for f in sorted((Path(out) / "vision").glob("*.jsonl")):
        recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        if recs:
            s = vision_summary(recs)
            rows.append({"model": recs[0]["method"], "input": f"image {recs[0]['ppm']:g} px/mm", "protocol": "lomo",
                         **{k: s.get(k) for k in ("n", "exact_hash", "topology_ok", "tray_ok", "triage_ok", "edge_negatives",
                                                  "edge_negatives_rejected", "median_abs_len_err_mm")},
                         "valid": s["detected"], "obs_consistent": None, "median_abs_meas_err_mm": s["median_abs_meas_err_mm"]})
    keys = ["model", "input", "protocol", "n", "valid", "obs_consistent", "exact_hash", "topology_ok", "tray_ok", "triage_ok",
            "edge_negatives", "edge_negatives_rejected", "median_abs_len_err_mm", "median_abs_meas_err_mm"]
    p = Path(out) / "compare.csv"; p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    return rows


def _pick(x):
    return {k: x.get(k) for k in ("n", "valid", "obs_consistent", "exact_hash", "topology_ok", "tray_ok", "triage_ok",
                                  "edge_negatives", "edge_negatives_rejected", "median_abs_len_err_mm")}


def main(argv=None):
    global STUDENT
    import argparse
    ap = argparse.ArgumentParser("baebugs-model-compare")
    ap.add_argument("what", choices=["text", "vision", "table"])
    ap.add_argument("--models", default="qwen3:1.7b,qwen2.5:1.5b,lfm2.5-1.2b-instruct:q4_k_m,lfm2.5-1.2b-thinking:q4_k_m")
    ap.add_argument("--protocols", default="lomo,lofo,s2l,l2s")
    ap.add_argument("--methods", default="classical,yolo,yoloe,vlm:qwen2.5vl:3b")
    ap.add_argument("--ppm", default="5,10,20")
    ap.add_argument("--student", default=STUDENT)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--render-dir", help="where renders go (default under --out; keep out of git)")
    ap.add_argument("--ledger", action="store_true")
    a = ap.parse_args(argv)
    STUDENT = a.student
    led = _ledger(a.ledger)
    if a.what == "text":
        run_text(a.models.split(","), a.protocols.split(","), ledger=led, limit=a.limit)
    elif a.what == "vision":
        run_vision(a.methods.split(","), [float(x) for x in a.ppm.split(",")], ledger=led, limit=a.limit,
                   render_dir=a.render_dir)
    rows = table()
    for r in rows:
        print(r)
    if led is not None:
        led.append("compare_table", {"rows": len(rows)}, files={"compare": Path(OUT) / "compare.csv"})


if __name__ == "__main__":
    main()
