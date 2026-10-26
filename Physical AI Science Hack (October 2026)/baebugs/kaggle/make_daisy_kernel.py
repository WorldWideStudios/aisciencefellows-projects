"""Build the Kaggle notebook + kernel-metadata for DAISY-BB-001 from the frozen
protocol JSON (daisy/DAISY-BB-001.json). The protocol JSON (dataset roots,
runs, settings, pinned baebugs commit) is embedded verbatim in the notebook and
its sha256 is checked at run time.

  python kaggle/make_daisy_kernel.py --user biobitworks --out kaggle/daisy_bb_001
"""
import argparse
import hashlib
import json
from pathlib import Path

import nbformat as nbf

CUSTODY = r'''
import hashlib, json, os
from pathlib import Path

def sha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def leaf(rec):
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

from baebugs.explore import merkle_root

ROOT = Path("/kaggle/input")
for p in sorted(ROOT.glob("*")) + sorted(ROOT.glob("*/*")) + sorted(ROOT.glob("*/*/*")):
    print("mount:", p)
POINTERS = list(ROOT.rglob("DAISY_POINTERS.jsonl"))

def find_member(bundle, name):
    """Kaggle has mounted datasets at /kaggle/input/<slug>/ and deeper
    (/kaggle/input/datasets/<user>/<slug>/...): search recursively, prefer a path inside the bundle."""
    hits = [p.parent for p in POINTERS if p.parent.name == name]
    inb = [h for h in hits if bundle in str(h)]
    return (inb or hits or [None])[0]

MEMBERS, CUSTODY_REPORT = {}, {}
for bundle, names in PROTO["bundles"].items():
    for name in names:
        d = find_member(bundle, name)
        if d is None:
            raise SystemExit(f"CUSTODY FAIL: {bundle}/{name} not mounted")
        pts = [json.loads(l) for l in (d / "DAISY_POINTERS.jsonl").read_text().splitlines() if l.strip()]
        bad = [p["path"] for p in pts if not (d / p["path"]).exists() or sha(d / p["path"]) != p["sha256"]]
        root = merkle_root([leaf(p) for p in pts])
        ok = not bad and root == PROTO["roots"][name]
        CUSTODY_REPORT[name] = {"files": len(pts), "bad_files": len(bad), "root": root, "expected": PROTO["roots"][name], "ok": ok}
        print(f"{name:26s} files={len(pts):6d} bad={len(bad):3d} root_ok={root == PROTO['roots'][name]}")
        if not ok:
            raise SystemExit(f"CUSTODY FAIL (fail closed): {name} bad={bad[:3]} root={root}")
        MEMBERS[name] = d
print("custody: all members verified")
'''

TRAIN = r'''
import yaml, time, math, platform, torch, ultralytics, pandas as pd
from ultralytics import YOLO
WORK = Path("/kaggle/working/daisy"); WORK.mkdir(parents=True, exist_ok=True)
EVENTS = []
def event(kind, payload):
    rec = {"t": time.time(), "kind": kind, "payload": payload}
    rec["leaf"] = leaf({k: v for k, v in rec.items()})
    EVENTS.append(rec)
    with open(WORK / "events.jsonl", "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
    return rec
event("custody", CUSTODY_REPORT)
event("protocol", {"sha256": PROTO_SHA, "id": PROTO["id"]})
S = PROTO["settings"]; G = PROTO.get("gates", {}); VAR = PROTO.get("variance", {})

def split_dirs(name, split):
    d = MEMBERS[name] / "images" / split
    return [str(d)] if d.exists() else []

def data_yaml(run, train_members, val_members):
    y = {"names": {0: "specimen"},
         "train": [p for m in train_members for p in split_dirs(m, "train")],
         "val": [p for m in val_members for p in split_dirs(m, "val")]}
    fp = WORK / f"{run}.yaml"; fp.write_text(yaml.safe_dump(y)); return fp

# G2 initial weights: hash must equal the pinned value (fail closed)
init = YOLO(S["model"]); init_sha = sha(S["model"]) if os.path.exists(S["model"]) else None
g2 = init_sha is not None and (not S.get("init_sha256") or init_sha == S["init_sha256"])
event("gate_G2_init_weights", {"claim": "init weights sha256 == pinned", "observed": init_sha,
                               "expected": S.get("init_sha256"), "pass": g2})
if not g2:
    raise SystemExit(f"G2 FAIL: init weights {init_sha} != pinned {S.get('init_sha256')}")

# G3a environment: recorded; unpinned / mismatched versions flagged (variance accepted, evidence kept)
env = {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
       "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "ultralytics": ultralytics.__version__}
flags = [k for k, v in S.get("pins", {}).items() if str(env.get(k)) != str(v)]
event("gate_G3a_environment", {"claim": "environment matches pins", "observed": env, "pins": S.get("pins", {}),
                               "flags": flags, "pass": not flags, "accepted_variance": True})

def finite_last(csvp):
    df = pd.read_csv(csvp); df.columns = [c.strip() for c in df.columns]
    cols = [c for c in df.columns if c.startswith("train/") and c.endswith("_loss")]
    row = df.iloc[-1]
    vals = {c: float(pd.to_numeric(row[c], errors="coerce")) for c in cols}
    return all(math.isfinite(v) for v in vals.values()), vals

# G3b smoke: AMP is a conditional step decided by evidence, not a fixed setting
smoke_run = PROTO["runs"][min(2, len(PROTO["runs"]) - 1)]          # 001: the all-data run; 002: last run
dy = data_yaml("smoke", smoke_run["train"], smoke_run["val"])
smoke = {}
for amp in (False, True):
    nm = f"smoke_amp_{amp}"
    try:
        YOLO(S["model"]).train(data=str(dy), epochs=1, fraction=G.get("smoke_fraction", 0.05), imgsz=S["imgsz"],
                               batch=S["batch"], seed=S["seed"], deterministic=S.get("deterministic", False), amp=amp,
                               project=str(WORK / "smoke"), name=nm, exist_ok=True, workers=S["workers"], plots=False,
                               verbose=False, val=False)
        fin, vals = finite_last(WORK / "smoke" / nm / "results.csv")
    except Exception as e:
        fin, vals = False, {"error": str(e)[:200]}
    smoke[amp] = {"finite": fin, "losses": vals}
agree = None
if smoke[False]["finite"] and smoke[True]["finite"]:
    rel = [abs(smoke[True]["losses"][c] - smoke[False]["losses"][c]) / max(abs(smoke[False]["losses"][c]), 1e-9)
           for c in smoke[False]["losses"]]
    agree = max(rel) <= VAR.get("smoke_loss_rel", 0.25)
USE_AMP = bool(smoke[True]["finite"] and agree)
event("gate_G3b_amp_smoke", {"claim": "AMP losses finite and within variance of fp32", "fp32": smoke[False], "amp": smoke[True],
                             "policy": {"smoke_loss_rel": VAR.get("smoke_loss_rel", 0.25)}, "agree": agree,
                             "decision_amp": USE_AMP, "pass": smoke[False]["finite"]})
if not smoke[False]["finite"]:
    raise SystemExit("G3b FAIL: fp32 smoke training is not finite -> data or environment problem, not AMP")

# G3c per-epoch evidence; first non-finite epoch is the break point and stops that run
def _nums(x):
    """flatten tensors / lists / dicts of numbers to a list of floats (ultralytics 8.4 nests some values)."""
    if hasattr(x, "tolist"):
        x = x.tolist()
    if isinstance(x, dict):
        return [v for k in sorted(x) for v in _nums(x[k])]
    if isinstance(x, (list, tuple)):
        return [v for i in x for v in _nums(i)]
    try:
        return [float(x)]
    except (TypeError, ValueError):
        return []

def epoch_gate(run_name):
    def cb(trainer):
        try:
            losses = _nums(trainer.tloss)
            fin = bool(losses) and all(math.isfinite(v) for v in losses)
            mp = {k: _nums(v)[0] for k, v in (trainer.metrics or {}).items() if "mAP" in k and _nums(v)}
            event("gate_G3c_epoch", {"run": run_name, "epoch": int(trainer.epoch) + 1, "losses": losses, "finite": fin,
                                     "map": mp, "pass": fin})
        except Exception as e:                       # the gate itself failed: recorded, fail closed
            fin = False
            event("gate_G3c_epoch", {"run": run_name, "epoch": int(getattr(trainer, "epoch", -1)) + 1,
                                     "error": f"{type(e).__name__}: {e}"[:300], "pass": False})
        if not fin:
            trainer.stop = True
    return cb

def weights_track(run_name):
    """every saved checkpoint is hashed when it is written: a realization is tracked epoch by epoch"""
    def cb(trainer):
        rec = {"run": run_name, "epoch": int(trainer.epoch) + 1}
        for k in ("last", "best"):
            f = getattr(trainer, k, None)
            rec[f"{k}_sha256"] = sha(f) if f and os.path.exists(f) else None
        event("weights_epoch", rec)
    return cb

def keep(path, name):
    """copy a weights file to the output and prove the copy is byte-identical"""
    import shutil
    dst = WORK / name
    shutil.copy2(path, dst)
    return sha(dst)

RESULTS = {}
for run in PROTO["runs"]:
    name = run["name"]; t0 = time.time()
    dy = data_yaml(name, run["train"], run["val"])
    m = YOLO(S["model"]); m.add_callback("on_fit_epoch_end", epoch_gate(name)); m.add_callback("on_model_save", weights_track(name))
    status, err = "EXECUTED", None
    try:
        m.train(data=str(dy), epochs=S["epochs"], imgsz=S["imgsz"], batch=S["batch"], seed=S["seed"],
                deterministic=S.get("deterministic", False), patience=10_000, project=str(WORK / "runs"), name=name,
                exist_ok=True, workers=S["workers"], plots=False, verbose=False, amp=USE_AMP)
    except Exception as e:
        status, err = "FAILED", str(e)[:300]
    eps = [e for e in EVENTS if e["kind"] == "gate_G3c_epoch" and e["payload"]["run"] == name]
    bad = next((e["payload"]["epoch"] for e in eps if not e["payload"]["pass"]), None)
    if bad is not None:
        status = "FAILED"
    best = WORK / "runs" / name / "weights" / "best.pt"
    wsha = sha(best) if best.exists() else None
    kept = keep(best, f"{name}_best.pt") if best.exists() else None          # saved NOW, before eval/cleanup
    event("weights_saved", {"run": name, "weights_sha256": wsha, "exported_sha256": kept, "file": f"{name}_best.pt",
                            "pass": wsha is not None and kept == wsha})
    RESULTS[name] = {"train": run["train"], "val": run["val"], "status": status, "error": err, "break_epoch": bad,
                     "epoch_root": merkle_root([e["leaf"] for e in eps]) if eps else None, "amp": USE_AMP,
                     "weights_sha256": wsha, "weights_file": f"{name}_best.pt" if kept else None,
                     "weights_epochs": [e["payload"] for e in EVENTS if e["kind"] == "weights_epoch" and e["payload"]["run"] == name],
                     "minutes": round((time.time() - t0) / 60, 1)}
    event("train_done", {"run": name, **RESULTS[name]})
    print(name, RESULTS[name])
'''

EVAL = r'''
import numpy as np, cv2
from baebugs.measure import YoloMeasurer

def val_metrics(weights, member, split):
    d = MEMBERS[member] / "images" / split
    if not d.exists():
        return None
    fp = WORK / f"eval_{member}_{split}.yaml"
    fp.write_text(yaml.safe_dump({"names": {0: "specimen"}, "train": str(d), "val": str(d)}))
    r = YOLO(weights).val(data=str(fp), imgsz=S["imgsz"], batch=S["batch"], plots=False, verbose=False,
                          project=str(WORK / "val"), name=f"{member}_{split}", exist_ok=True)
    return {"mask_map50_95": round(float(r.seg.map), 4), "mask_map50": round(float(r.seg.map50), 4),
            "box_map50_95": round(float(r.box.map), 4)}

def toy_size_error(weights):
    truth = json.loads((MEMBERS["toy_renders"] / "truth.json").read_text())
    meas = YoloMeasurer(weights, conf=0.15)
    out = {}
    for ppm in (10, 20):
        rows = [t for t in truth if t["px_per_mm"] == ppm]
        el, ew, det = [], [], 0
        for t in rows:
            img = cv2.imread(str(MEMBERS["toy_renders"] / t["image"]))
            ms = meas(img, ppm)
            if not ms:
                continue
            det += 1
            b = max(ms, key=lambda x: x.area_mm2)
            L, W = max(t["envelope_mm"][:2]), min(t["envelope_mm"][:2])
            el.append(abs(b.length_mm - L) / L); ew.append(abs(b.width_mm - W) / W)
        out[f"ppm{ppm}"] = {"n": len(rows), "detected": det,
                            "median_rel_len_err": round(float(np.median(el)), 4) if el else None,
                            "median_rel_wid_err": round(float(np.median(ew)), 4) if ew else None}
    return out

def ruler_truth_error(weights, member):
    tp = MEMBERS[member] / "truth_real_val.json"
    if not tp.exists():
        return None
    truth = json.loads(tp.read_text()); meas = YoloMeasurer(weights, conf=0.15)
    errs = []
    for t in truth:
        img = cv2.imread(str(MEMBERS[member] / t["image"]))
        if img is None or not t.get("objects"):
            continue
        ms = meas(img, t["px_per_mm"])
        for o in t["objects"]:
            if not ms:
                errs.append(1.0); continue
            b = min(ms, key=lambda x: (x.cx - o["cx"]) ** 2 + (x.cy - o["cy"]) ** 2)
            errs.append(abs(b.length_mm - o["length_mm"]) / o["length_mm"])
    return {"objects": len(errs), "median_rel_len_err": round(float(np.median(errs)), 4) if errs else None}

ALL_VAL = [n for b in PROTO["bundles"].values() for n in b if n not in ("toy_renders",)]
for name, res in RESULTS.items():
    if res["status"] != "EXECUTED":
        continue
    w = str(WORK / "runs" / name / "weights" / "best.pt")
    res["eval"] = {m: val_metrics(w, m, "val") for m in ALL_VAL}
    res["toy"] = toy_size_error(w)
    res["toy_val"] = {f"ppm{p}": val_metrics(w, "toy_renders", f"ppm{p}") for p in (10, 20)}
    res["ruler_truth"] = {m: ruler_truth_error(w, m) for m in MEMBERS if (MEMBERS[m] / "truth_real_val.json").exists()}
    res["status"] = "OBSERVED_EXPLORATORY"
    event("eval_done", {"run": name, "eval": res["eval"], "toy": res["toy"], "ruler_truth": res["ruler_truth"]})
    print(name, json.dumps(res["toy"]), json.dumps(res["ruler_truth"]))
'''

FINISH = r'''
# custody check (fail closed): every weights hash must resolve to an exported file with the same bytes
breaks = []
for name, r in RESULTS.items():
    if r.get("weights_sha256"):
        f = WORK / (r.get("weights_file") or f"{name}_best.pt")
        got = sha(f) if f.exists() else None
        if got != r["weights_sha256"]:
            breaks.append({"run": name, "expected": r["weights_sha256"], "found": got, "file": str(f.name)})
            r["custody"] = "BROKEN"
        else:
            r["custody"] = "INTACT"
event("custody_check", {"weights_breaks": breaks, "pass": not breaks})
import shutil
shutil.rmtree(WORK / "runs", ignore_errors=True); shutil.rmtree(WORK / "val", ignore_errors=True)
artifacts = {str(p.relative_to(WORK)): sha(p) for p in sorted(WORK.rglob("*")) if p.is_file() and p.name != "results.json"}
root = merkle_root([e["leaf"] for e in EVENTS])
summary = {"protocol": PROTO["id"], "protocol_sha256": PROTO_SHA, "custody": CUSTODY_REPORT, "results": RESULTS,
           "events_root": root, "n_events": len(EVENTS), "artifacts": artifacts,
           "artifacts_root": merkle_root(sorted(artifacts.values())) if artifacts else None,
           "custody_status": "BROKEN" if breaks else "INTACT", "custody_breaks": breaks,
           "admission": "no automatic promotion; best variant at most VALIDATION_CANDIDATE"}
(WORK / "results.json").write_text(json.dumps(summary, indent=1, default=str))
print("events root", root, "custody", summary["custody_status"])
if breaks:
    raise SystemExit(f"CUSTODY BREAK: weights referenced by hash but not exported: {breaks}")
'''


def build(proto_path, out_dir, user):
    proto_txt = Path(proto_path).read_text()
    proto = json.loads(proto_txt)
    psha = hashlib.sha256(proto_txt.encode()).hexdigest()
    fam = proto["id"].split("-")[-1].rstrip("abcdefgh").lower()          # 001b -> 001 (same Kaggle kernel)
    nb = nbf.v4.new_notebook()
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    nb.cells = [
        md(f"# {proto['id']} — DAISY verified-data training (baebugs)\n\nFrozen protocol: `daisy/{proto['id']}.json` "
           f"(sha256 `{psha}`). Gate 0 recomputes every staged file hash and member Merkle root and **stops on any mismatch**. "
           "Results are OBSERVED_EXPLORATORY; nothing is promoted automatically. Toy renders are parametric TOYS, not replicas."),
        code(f"!pip -q install ultralytics=={proto['settings']['ultralytics']} shapely trimesh manifold3d pyyaml\n"
             f"!pip -q install --no-deps git+https://github.com/biobitworks/baebugs.git@{proto['baebugs_commit']}"),
        code("import json, hashlib\nPROTO_TXT = " + json.dumps(proto_txt) +
             "\nPROTO = json.loads(PROTO_TXT)\nPROTO_SHA = hashlib.sha256(PROTO_TXT.encode()).hexdigest()\n"
             f"assert PROTO_SHA == {psha!r}, 'protocol changed'\nprint(PROTO['id'], PROTO_SHA)"),
        md("## Gate 0 — custody (fail closed)"), code(CUSTODY),
        md("## Frozen runs"), code(TRAIN),
        md("## Evaluation: every member val, toy renders (exact truth), ruler truth"), code(EVAL),
        md("## Outputs + event Merkle root"), code(FINISH),
    ]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, out / f"daisy_bb_{fam}.ipynb")
    (out / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/baebugs-daisy-bb-{fam}", "title": f"baebugs DAISY-BB-{fam}", "code_file": f"daisy_bb_{fam}.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True, "enable_gpu": True,
        "enable_internet": True, "dataset_sources": [f"{user}/{b}" for b in proto["bundles"]],
        "competition_sources": [], "kernel_sources": []}, indent=1))
    return psha


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--proto", default="daisy/DAISY-BB-001.json")
    ap.add_argument("--out", default="kaggle/daisy_bb_001")
    ap.add_argument("--user", default="biobitworks")
    a = ap.parse_args()
    print(build(a.proto, a.out, a.user))
