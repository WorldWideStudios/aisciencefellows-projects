"""Build the DAISY-BB-004 Kaggle kernel (per-taxon preprocessors, yolo-cls) from the frozen protocol.

Custody built in: G0 protocol sha, G1 every crop + view file re-hashed against crops.jsonl and the
frozen Merkle root, G2 init weights sha (pinned), per-epoch weights tracking (file sha + canonical tensor
sha) and values, weights kept and verified right after each run, fail-closed custody_check, artifact
manifest + root. Decision: preprocessor USEFUL if test macro-F1 beats the majority baseline by > 0.10.
"""
import argparse
import hashlib
import json
from pathlib import Path

import nbformat as nbf

CODE = r'''
import os, json, math, time, hashlib, platform, shutil
from pathlib import Path
import torch, ultralytics
from ultralytics import YOLO
WORK = Path(os.environ.get("DAISY_WORK", "/kaggle/working/daisy004")); WORK.mkdir(parents=True, exist_ok=True)
EVENTS = []
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
def H(o): return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
def merkle_root(leaves):
    lv = list(leaves)
    if not lv: return None
    while len(lv) > 1:
        if len(lv) % 2: lv.append(lv[-1])
        lv = [hashlib.sha256((a + b).encode()).hexdigest() for a, b in zip(lv[::2], lv[1::2])]
    return lv[0]
def event(kind, payload):
    e = {"i": len(EVENTS), "kind": kind, "t": round(time.time(), 3), "payload": payload, "prev": EVENTS[-1]["leaf"] if EVENTS else None}
    e["leaf"] = H(e); EVENTS.append(e)
    with open(WORK / "events.jsonl", "a") as f: f.write(json.dumps(e, default=str) + "\n")
    return e
def tensor_sha(p):
    ck = torch.load(p, map_location="cpu", weights_only=False)
    m = ck.get("ema") or ck.get("model")
    sd = m.float().state_dict()
    h = hashlib.sha256()
    for k in sorted(sd):
        h.update(k.encode()); h.update(sd[k].detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
event("protocol", {"id": PROTO["id"], "sha256": PROTO_SHA})

# G1 custody: crops + views re-hashed against the frozen manifest and root (fail closed)
cj = next(Path(os.environ.get("DAISY_INPUT", "/kaggle/input")).rglob("crops.jsonl"))
BASE = cj.parent
recs = [json.loads(l) for l in cj.read_text().splitlines() if l.strip()]
bad = [r["path"] for r in recs if not (BASE / r["path"]).exists() or sha(BASE / r["path"]) != r["sha256"]]
root = merkle_root(sorted(hashlib.sha256(f"{r['path']}\0{r['sha256']}".encode()).hexdigest() for r in recs))
known = {r["sha256"] for r in recs}
view_bad = [str(p) for p in (BASE / "views").rglob("*.jpg") if sha(p) not in known]
g1 = not bad and not view_bad and root == PROTO["data_root"]
event("gate_G1_custody", {"crops": len(recs), "bad": bad[:5], "view_bad": view_bad[:5], "root": root, "expected": PROTO["data_root"], "pass": g1})
if not g1: raise SystemExit(f"G1 FAIL custody: bad={len(bad)} view_bad={len(view_bad)} root={root}")

# G2 init weights
S = PROTO["settings"]
init = YOLO(S["model"]); isha = sha(S["model"]) if os.path.exists(S["model"]) else None
g2 = isha is not None and (not S.get("init_sha256") or isha == S["init_sha256"])
event("gate_G2_init_weights", {"observed": isha, "expected": S.get("init_sha256"), "pass": g2})
if not g2: raise SystemExit("G2 FAIL init weights")
env = {"python": platform.python_version(), "torch": torch.__version__, "cuda": torch.version.cuda,
       "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, "ultralytics": ultralytics.__version__,
       "platform": platform.platform(), "machine": platform.machine(), "torch_threads": torch.get_num_threads(),
       "device": os.environ.get("DAISY_DEVICE") or "auto"}
event("gate_G3a_environment", {"observed": env, "pins": S.get("pins", {}), "pass": all(str(env.get(k)) == str(v) for k, v in S.get("pins", {}).items())})

def loss_values(t):
    """Training loss as floats: Ultralytics 8.4 keeps tloss as a dict {name: tensor}; older versions as a tensor."""
    if t is None: return []
    if isinstance(t, dict): t = list(t.values())
    if hasattr(t, "reshape"): t = t.reshape(-1).tolist()
    out = []
    for x in (t if isinstance(t, (list, tuple)) else [t]):
        try: out += [float(v) for v in (x.reshape(-1).tolist() if hasattr(x, "reshape") else [x])]
        except Exception: return []
    return out

def track(run):
    def on_save(tr):
        rec = {"run": run, "epoch": int(tr.epoch) + 1}
        for k in ("last", "best"):
            f = getattr(tr, k, None)
            if f and os.path.exists(f): rec[f"{k}_sha256"] = sha(f); rec[f"{k}_tensor_sha256"] = tensor_sha(f)
        event("weights_epoch", rec)
    seen = {}
    def on_train_epoch(tr):
        # capture the training loss before validation (ultralytics may reset tloss by on_fit_epoch_end)
        seen[int(tr.epoch)] = loss_values(tr.tloss)
    def on_epoch(tr):
        vals = {}
        for k, v in (tr.metrics or {}).items():
            try: vals[k] = float(v)
            except Exception: pass
        loss = seen.get(int(tr.epoch), [])
        fin = bool(loss) and all(math.isfinite(x) for x in loss)
        event("values_epoch", {"run": run, "epoch": int(tr.epoch) + 1, "loss": loss, "metrics": vals, "finite": fin, "pass": fin})
        if not fin: tr.stop = True
    return on_save, on_train_epoch, on_epoch

def evaluate(w, split_dir):
    m = YOLO(w); classes = sorted(p.name for p in split_dir.iterdir() if p.is_dir())
    y, yhat = [], []
    for c in classes:
        for f in sorted((split_dir / c).glob("*.jpg")):
            r = m.predict(str(f), verbose=False, imgsz=S["imgsz"])[0]
            y.append(c); yhat.append(r.names[int(r.probs.top1)])
    if not y: return None
    labels = sorted(set(y))
    def f1(c):
        tp = sum(1 for a, b in zip(y, yhat) if a == c and b == c); fp = sum(1 for a, b in zip(y, yhat) if a != c and b == c)
        fn = sum(1 for a, b in zip(y, yhat) if a == c and b != c)
        return 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)
    maj = max(labels, key=lambda c: y.count(c))
    base = (2 * y.count(maj) / (len(y) + y.count(maj))) / len(labels)          # macro-F1 of always predicting the majority class
    return {"n": len(y), "top1": round(sum(a == b for a, b in zip(y, yhat)) / len(y), 4),
            "macro_f1": round(sum(f1(c) for c in labels) / len(labels), 4), "majority_macro_f1": round(base, 4),
            "per_class_f1": {c: round(f1(c), 4) for c in labels}}

RESULTS = {}
for run in PROTO["runs"]:
    name = run["name"]; vdir = BASE / "views" / name; t0 = time.time()
    m = YOLO(S["model"]); on_save, on_train_epoch, on_epoch = track(name)
    m.add_callback("on_model_save", on_save); m.add_callback("on_train_epoch_end", on_train_epoch); m.add_callback("on_fit_epoch_end", on_epoch)
    status, err = "EXECUTED", None
    try:
        m.train(data=str(vdir), epochs=S["epochs"], imgsz=S["imgsz"], batch=S["batch"], seed=S["seed"],
                deterministic=S.get("deterministic", False), workers=S["workers"], device=os.environ.get("DAISY_DEVICE") or None, plots=False, verbose=False,
                project=str(WORK / "runs"), name=name, exist_ok=True, val=True, split="val")
    except Exception as e:
        status, err = "FAILED", f"{type(e).__name__}: {e}"[:300]
    best = WORK / "runs" / name / "weights" / "best.pt"
    wsha = sha(best) if best.exists() else None
    kept = None
    if best.exists():
        shutil.copy2(best, WORK / f"{name}_best.pt"); kept = sha(WORK / f"{name}_best.pt")
    tsha = tensor_sha(WORK / f"{name}_best.pt") if kept else None
    event("weights_saved", {"run": name, "weights_sha256": wsha, "exported_sha256": kept, "tensor_sha256": tsha, "pass": wsha is not None and kept == wsha})
    ev = {}
    if kept:
        for sp in ("val", "test"):
            if (vdir / sp).exists() and any((vdir / sp).iterdir()):
                ev[sp] = evaluate(str(WORK / f"{name}_best.pt"), vdir / sp)
    t = ev.get("test")
    verdict = None if not t else ("USEFUL" if t["macro_f1"] - t["majority_macro_f1"] > PROTO["decision"]["margin"] else "NULL")
    RESULTS[name] = {"status": status if status != "EXECUTED" else "OBSERVED_EXPLORATORY", "error": err, "classes": run["classes"],
                     "weights_sha256": wsha, "weights_tensor_sha256": tsha, "weights_file": f"{name}_best.pt" if kept else None,
                     "eval": ev, "verdict": verdict, "minutes": round((time.time() - t0) / 60, 1)}
    event("run_done", {"run": name, **{k: v for k, v in RESULTS[name].items() if k != "eval"}, "eval": ev})
    print(name, json.dumps(RESULTS[name])[:600])

# custody check (fail closed)
breaks = []
for name, r in RESULTS.items():
    if r["weights_sha256"]:
        f = WORK / r["weights_file"] if r["weights_file"] else None
        got = sha(f) if f and f.exists() else None
        r["custody"] = "INTACT" if got == r["weights_sha256"] else "BROKEN"
        if r["custody"] == "BROKEN": breaks.append({"run": name, "expected": r["weights_sha256"], "found": got})
event("custody_check", {"weights_breaks": breaks, "pass": not breaks})
shutil.rmtree(WORK / "runs", ignore_errors=True)
artifacts = {str(p.relative_to(WORK)): sha(p) for p in sorted(WORK.rglob("*")) if p.is_file() and p.name != "results.json"}
summary = {"protocol": PROTO["id"], "protocol_sha256": PROTO_SHA, "results": RESULTS, "events_root": merkle_root([e["leaf"] for e in EVENTS]),
           "n_events": len(EVENTS), "artifacts": artifacts, "artifacts_root": merkle_root(sorted(artifacts.values())),
           "custody_status": "BROKEN" if breaks else "INTACT", "custody_breaks": breaks}
(WORK / "results.json").write_text(json.dumps(summary, indent=1, default=str))
print("custody", summary["custody_status"], "events root", summary["events_root"])
if breaks: raise SystemExit(f"CUSTODY BREAK {breaks}")
'''


def build(proto_path, out_dir, user="biobitworks"):
    txt = Path(proto_path).read_text(); proto = json.loads(txt); psha = hashlib.sha256(txt.encode()).hexdigest()
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(f"# {proto['id']} — per-taxon preprocessors (baebugs)\n\nFrozen protocol sha256 `{psha}`. "
                                         "Gates fail closed; weights and values tracked every epoch; results OBSERVED_EXPLORATORY."),
                nbf.v4.new_code_cell(f"!pip -q install ultralytics=={proto['settings']['ultralytics']}"),
                nbf.v4.new_code_cell("import json, hashlib\nPROTO_TXT = " + json.dumps(txt) + "\nPROTO = json.loads(PROTO_TXT)\n"
                                     "PROTO_SHA = hashlib.sha256(PROTO_TXT.encode()).hexdigest()\n"
                                     f"assert PROTO_SHA == {psha!r}, 'protocol changed'"),
                nbf.v4.new_code_cell(CODE)]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, out / "daisy_bb_004.ipynb")
    (out / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/baebugs-daisy-bb-004", "title": "baebugs DAISY-BB-004", "code_file": "daisy_bb_004.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True, "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [f"{user}/{proto['bundle']}"], "competition_sources": [], "kernel_sources": []}, indent=1))
    return psha


def run_local(proto_path, input_dir, work_dir, device=None):
    """Run the identical kernel code on this machine (CPU): same gates, same custody, bytes land in work_dir."""
    import os
    txt = Path(proto_path).read_text()
    os.environ["DAISY_INPUT"] = str(Path(input_dir).resolve()); os.environ["DAISY_WORK"] = str(Path(work_dir).resolve())
    if device:
        os.environ["DAISY_DEVICE"] = device
    g = {"PROTO_TXT": txt, "PROTO": json.loads(txt), "PROTO_SHA": hashlib.sha256(txt.encode()).hexdigest(), "__name__": "__daisy__"}
    exec(compile(CODE, "daisy_bb_004_kernel", "exec"), g)  # noqa: S102 - the frozen kernel code itself, unmodified
    return g["summary"]


def freeze(report_path, out="daisy/DAISY-BB-004.json", init_sha=None):
    import subprocess
    rep = json.loads(Path(report_path).read_text())
    if rep["leakage_media_ids"]:
        raise SystemExit("refusing to freeze: media-id leakage")
    prev = json.loads(Path("daisy/DAISY-BB-001b.json").read_text())
    proto = {"id": "DAISY-BB-004", "status": "PROPOSED",
             "baebugs_commit": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
             "preregistration": {"path": "daisy/DAISY-BB-004-prereg.md",
                                 "sha256": hashlib.sha256(Path("daisy/DAISY-BB-004-prereg.md").read_bytes()).hexdigest()},
             "bundle": "baebugs-daisy-taxon", "data_root": rep["merkle_root"], "crops": rep["crops"], "licences": rep["licences"],
             "runs": [{"name": k, "classes": v["classes"], "counts": v["counts"]} for k, v in rep["runs"].items()],
             "settings": {"model": "yolo11n-cls.pt", "init_sha256": init_sha, "ultralytics": prev["settings"]["ultralytics"],
                          "pins": prev["settings"].get("pins", {}), "epochs": 15, "imgsz": 224, "batch": 64, "seed": 2026,
                          "deterministic": False, "workers": 4},
             "gates": {"G0": "protocol sha", "G1": "every crop + view file re-hashed; data root == frozen", "G2": "init weights sha == pinned",
                       "G3a": "environment recorded", "values_epoch": "losses finite every epoch", "custody_check": "every weights hash resolves to an exported file"},
             "decision": {"metric": "test macro-F1 minus majority-class macro-F1", "margin": 0.10},
             "variance": prev["variance"], "licence_note": "trained weights fall under AGPL-3.0 (Ultralytics); crops CC0/CC BY 4.0 per record"}
    Path(out).write_text(json.dumps(proto, indent=1, sort_keys=True))
    return proto


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["freeze", "build", "local"])
    ap.add_argument("--input"); ap.add_argument("--work"); ap.add_argument("--device")
    ap.add_argument("--report"); ap.add_argument("--init-sha")
    ap.add_argument("--proto", default="daisy/DAISY-BB-004.json"); ap.add_argument("--out", default="kaggle/daisy_bb_004")
    a = ap.parse_args()
    if a.cmd == "freeze":
        print(freeze(a.report, a.proto, a.init_sha)["data_root"])
    elif a.cmd == "local":
        print(json.dumps(run_local(a.proto, a.input, a.work, a.device)["custody_status"]))
    else:
        print(build(a.proto, a.out))
