"""Merkle knowledge graph of pulled insect specimens, with a break point per
insect, LOMO across measuring methods, tray assignment and a decision matrix
for when a human steps in.

Graph:   graph root -> order roots -> family roots -> insect leaves
Leaf:    sha256 of the insect's canonical record (taxon from GBIF, image hash,
         ruler px/mm, size by every method, consensus, variance, shape, tray,
         decision). Family root = Merkle root of its leaves, and so on up.
Break points: every insect appended to kg/ledger.jsonl is a break point (leaf +
         running root over all leaves so far, chained by prev). Commits and
         pushes happen per family (or every `push_every` insects), so the repo
         history carries the roots without thousands of pushes.

Methods (independent ways to size the same insect; dry pinned specimens):
  teacher   YOLOE zero-shot 'insect' mask (also produced the pseudo-labels)
  student   trained baebugs YOLO-seg
  fastsam   FastSAM segment-anything mask at the insect's centre
  skimage   scikit-image regionprops on an Otsu mask in the insect's box
            (the ImageJ 'Analyze Particles' style standard; ellipse axes)
LOMO:    for each method, its error against the median of the OTHER methods;
         a method that disagrees with the rest is flagged, and removing a
         method shows how much the consensus depends on it.

Decision matrix (methods agree?  x  fits the database?):
             fits                       outside
  agree      AUTO  sieve on its tray    VIP   novel: human reviews
  disagree   LABEL human measures       STEP-IN  "?": human decides first
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from .explore import merkle_root
from .sieve import classify, load_yaml

METHODS = ("teacher", "student", "fastsam", "skimage")


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def load_taxa(manifests):
    tax = {}
    for m in manifests:
        p = Path(m)
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                tax[str(r["gbifID"])] = {k: r.get(k) for k in ("order", "family", "scientificName",
                                                                "institutionCode", "catalogNumber", "license")}
    return tax


def skimage_size(img, cx, cy, half_px, ppm):
    from skimage import filters, measure
    h, w = img.shape[:2]
    x0, y0 = int(max(0, cx - half_px)), int(max(0, cy - half_px))
    x1, y1 = int(min(w, cx + half_px)), int(min(h, cy + half_px))
    g = cv2.cvtColor(img[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    if g.size < 100:
        return None
    t = filters.threshold_otsu(g)
    lab = measure.label(g < t)
    regs = measure.regionprops(lab)
    if not regs:
        return None
    # the region nearest the box centre
    c = np.array([cy - y0, cx - x0])
    r = min(regs, key=lambda r: np.hypot(*(np.array(r.centroid) - c)) - 0.001 * r.area)
    return {"length_mm": r.axis_major_length / ppm, "width_mm": r.axis_minor_length / ppm}


def efd_shape(poly, order=10):
    import pyefd
    c = np.asarray(poly, float)
    if len(c) < 8:
        return None
    co = pyefd.elliptic_fourier_descriptors(c, order=order, normalize=True)
    return [round(float(v), 5) for v in co.flatten()[3:]]   # drop the 3 constant terms


def _nearest(ms, cx, cy, ppm, tol_mm=3.0):
    if not ms:
        return None
    d = [np.hypot(m.cx - cx, m.cy - cy) for m in ms]
    i = int(np.argmin(d))
    return ms[i] if d[i] < tol_mm * ppm else None


def measure_specimens(pseudo_dir, student_weights, taxa, limit=None, fastsam="FastSAM-s.pt"):
    from ultralytics import FastSAM

    from .measure import YoloMeasurer, _from_contour
    pseudo = Path(pseudo_dir)
    student = YoloMeasurer(str(student_weights), conf=0.15)
    fsam = FastSAM(fastsam)
    recs = []
    for split in ("train", "val"):
        tj = pseudo / f"truth_real_{split}.json"
        if not tj.exists():
            continue
        for rec in json.loads(tj.read_text()):
            recs.append((split, rec))
    recs = recs[:limit]
    for split, rec in recs:
        p = pseudo / rec["image"]
        img = cv2.imread(str(p))
        if img is None:
            continue
        ppm = rec["px_per_mm"]
        lab = (pseudo / "labels" / split / f"{p.stem}.txt")
        polys = []
        if lab.exists():
            h, w = img.shape[:2]
            for line in lab.read_text().splitlines():
                v = line.split()
                if len(v) > 6:
                    polys.append(np.array(v[1:], float).reshape(-1, 2) * [w, h])
        stu = student(img, ppm)
        fs = fsam.predict(img, imgsz=1024, retina_masks=True, conf=0.25, verbose=False)[0]
        fms = [_from_contour(np.asarray(xy, np.float32).reshape(-1, 1, 2), ppm, "fastsam")
               for xy in (fs.masks.xy if fs.masks is not None else []) if len(xy) >= 3]
        gid = p.stem
        for k, o in enumerate(rec["objects"]):
            sizes = {"teacher": {"length_mm": o["length_mm"], "width_mm": o["width_mm"]}}
            s = _nearest(stu, o["cx"], o["cy"], ppm)
            if s:
                sizes["student"] = {"length_mm": s.length_mm, "width_mm": s.width_mm}
            f = _nearest([m for m in fms if m.length_mm < 2.5 * o["length_mm"]], o["cx"], o["cy"], ppm)
            if f:
                sizes["fastsam"] = {"length_mm": f.length_mm, "width_mm": f.width_mm}
            sk = skimage_size(img, o["cx"], o["cy"], 0.8 * o["length_mm"] * ppm, ppm)
            if sk:
                sizes["skimage"] = sk
            poly = polys[k] if k < len(polys) else None
            yield {"insect_id": f"{gid}#{k}", "gbifID": gid, "split": split,
                   "image_sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                   "px_per_mm": round(ppm, 3), "ruler_conf": rec.get("ruler_conf"),
                   "taxon": taxa.get(gid, {}), "sizes": {m: {kk: round(vv, 3) for kk, vv in d.items()}
                                                          for m, d in sizes.items()},
                   "efd": efd_shape(poly) if poly is not None else None, "preservation": "dry (pinned)"}


def lomo_methods(insects):
    """Leave-one-method-out: each method vs the median of the others."""
    out = {}
    for m in METHODS:
        devs, by_order = [], defaultdict(list)
        for r in insects:
            ws = {k: v["width_mm"] for k, v in r["sizes"].items()}
            if m not in ws or len(ws) < 3:
                continue
            others = np.median([v for k, v in ws.items() if k != m])
            d = abs(ws[m] - others) / max(others, 1e-6)
            devs.append(d); by_order[r["taxon"].get("order") or "?"].append(d)
        if devs:
            out[m] = {"n": len(devs), "median_rel_dev": round(float(np.median(devs)), 4),
                      "p90_rel_dev": round(float(np.percentile(devs, 90)), 4),
                      "by_order": {o: round(float(np.median(v)), 4) for o, v in by_order.items() if len(v) >= 5}}
    return out


def decide(insects, cv_agree=0.10, novelty_pct=0.99, k=8):
    """Consensus size, variance, tray, novelty (leave-self-out within the graph,
    size + EFD shape), and the decision-matrix cell for every insect."""
    kit = load_yaml("insects.yaml")
    for r in insects:
        ws = [v["width_mm"] for v in r["sizes"].values()]
        ls = [v["length_mm"] for v in r["sizes"].values()]
        r["consensus"] = {"width_mm": round(float(np.median(ws)), 3), "length_mm": round(float(np.median(ls)), 3)}
        r["size_cv"] = round(float(np.std(ws) / max(np.mean(ws), 1e-6)), 4) if len(ws) > 1 else None
        r["n_methods"] = len(ws)
        cls = classify(r["consensus"]["width_mm"], kit["classes"])
        r["tray"] = next((c["sieve"] for c in kit["classes"] if c["name"] == cls), "out of range")
        r["size_class"] = cls
    # novelty: k-NN distance in (log L, log W, aspect, EFD) vs all OTHER insects
    feats = []
    for r in insects:
        L, W = r["consensus"]["length_mm"], r["consensus"]["width_mm"]
        e = r["efd"] or [0.0] * 37
        feats.append(np.r_[np.log(L), np.log(W), W / max(L, 1e-6), 0.5 * np.asarray(e[:12])])
    X = np.asarray(feats)
    D = np.linalg.norm(X[:, None] - X[None], axis=2)
    np.fill_diagonal(D, np.inf)
    kk = min(k, len(X) - 1)
    knn = np.sort(D, axis=1)[:, :kk].mean(axis=1)
    cut = np.quantile(knn, novelty_pct)
    for r, d in zip(insects, knn):
        r["novelty"] = round(float((knn < d).mean()), 4)
        agree = r["n_methods"] >= 3 and r["size_cv"] is not None and r["size_cv"] < cv_agree
        fits = d <= cut and r["tray"] != "out of range"
        r["decision"] = {(True, True): "AUTO", (True, False): "VIP",
                         (False, True): "LABEL", (False, False): "STEP-IN"}[(agree, fits)]
        r["human"] = r["decision"] != "AUTO"
        r["why"] = (([] if agree else [f"methods disagree (CV {r['size_cv']}, n={r['n_methods']})"]) +
                    ([] if fits else [f"outside database (novelty {r['novelty']:.3f}, tray {r['tray']})"]))
    return insects


class KGLedger:
    """Per-insect break points; commit + push per family / every N insects."""
    def __init__(self, repo, name="kg", push=True, push_every=200):
        self.repo = Path(repo); self.dir = self.repo / "kg"; self.dir.mkdir(exist_ok=True)
        self.path = self.dir / f"{name}_ledger.jsonl"; self.path.write_text("")
        self.leaves, self.push, self.push_every, self.pending = [], push, push_every, 0

    def append(self, insect):
        leaf = _h(insect)
        self.leaves.append(leaf)
        bp = {"n": len(self.leaves), "insect_id": insect["insect_id"], "leaf": leaf,
              "root": merkle_root(self.leaves), "decision": insect["decision"], "t": time.time()}
        with self.path.open("a") as f:
            f.write(json.dumps(bp) + "\n")
        self.pending += 1
        return bp

    def flush(self, msg):
        if not self.pending:
            return
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, text=True, check=False)
        g("add", "kg")
        g("-c", "user.name=biobitworks", "-c", "user.email=biobitworks@gmail.com", "commit", "-q", "-m",
          f"KG BP {msg} | insects {len(self.leaves)} | root {merkle_root(self.leaves)[:12]}\n\n"
          "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
        if self.push:
            for _ in range(3):
                g("pull", "-q", "--rebase", "--autostash")
                if g("push", "-q").returncode == 0:
                    break
                time.sleep(3)
        self.pending = 0


def build(pseudo_dir, student_weights, manifests, repo, limit=None, push=True):
    taxa = load_taxa(manifests)
    insects = list(measure_specimens(pseudo_dir, student_weights, taxa, limit=limit))
    decide(insects)
    insects.sort(key=lambda r: ((r["taxon"].get("order") or "~"), (r["taxon"].get("family") or "~"), r["insect_id"]))
    led = KGLedger(repo, push=push)
    fam_leaves, order_fams = defaultdict(list), defaultdict(dict)
    spec_path = Path(repo) / "kg" / "insects.jsonl"
    with spec_path.open("w") as f:
        cur_fam = None
        for r in insects:
            fam = (r["taxon"].get("order") or "?", r["taxon"].get("family") or "?")
            if cur_fam and fam != cur_fam and led.pending >= led.push_every:
                led.flush(f"through family {cur_fam[1]}")   # commit+push at a family boundary
            cur_fam = fam
            r["leaf"] = led.append(r)["leaf"]
            fam_leaves[fam].append(r["leaf"])
            f.write(json.dumps(r) + "\n")
    for (o, fa), lv in fam_leaves.items():
        order_fams[o][fa] = merkle_root(lv)
    orders = {o: merkle_root(sorted(fams.values())) for o, fams in order_fams.items()}
    graph = {"graph_root": merkle_root(sorted(orders.values())), "orders": orders,
             "families": {f"{o}/{fa}": {"root": merkle_root(lv), "n": len(lv)} for (o, fa), lv in fam_leaves.items()},
             "n_insects": len(insects)}
    lomo = lomo_methods(insects)
    matrix = defaultdict(int)
    for r in insects:
        matrix[r["decision"]] += 1
    (Path(repo) / "kg" / "graph.json").write_text(json.dumps(graph, indent=1))
    (Path(repo) / "kg" / "lomo_methods.json").write_text(json.dumps(lomo, indent=1))
    (Path(repo) / "kg" / "decision_matrix.json").write_text(json.dumps(dict(matrix), indent=1))
    led.flush(f"graph root {graph['graph_root'][:12]}")
    return graph, lomo, dict(matrix)


def write_dashboard_csvs(repo):
    import csv
    repo = Path(repo); out = repo / "dashboard" / "csv"; out.mkdir(parents=True, exist_ok=True)
    ins = [json.loads(l) for l in (repo / "kg" / "insects.jsonl").read_text().splitlines() if l.strip()]
    lomo = json.loads((repo / "kg" / "lomo_methods.json").read_text())
    def w(name, header, rows):
        with (out / f"{name}.csv").open("w", newline="") as f:
            wr = csv.writer(f); wr.writerow(header); wr.writerows(rows)
    agg = defaultdict(lambda: defaultdict(int))
    for r in ins:
        agg[r["tray"]][r["decision"]] += 1
    w("kg_matrix", ["tray", "AUTO", "VIP", "LABEL", "STEP-IN"],
      [[t, d["AUTO"], d["VIP"], d["LABEL"], d["STEP-IN"]] for t, d in sorted(agg.items())])
    w("kg_lomo", ["method", "n", "median_rel_dev", "p90_rel_dev"],
      [[m, v["n"], v["median_rel_dev"], v["p90_rel_dev"]] for m, v in lomo.items()])
    fam = defaultdict(list)
    for r in ins:
        fam[(r["taxon"].get("order") or "?", r["taxon"].get("family") or "?")].append(r)
    rows = []
    for (o, f), rs in fam.items():
        wd = [r["consensus"]["width_mm"] for r in rs]; cvs = [r["size_cv"] for r in rs if r["size_cv"] is not None]
        trays = defaultdict(int)
        for r in rs:
            trays[r["tray"]] += 1
        rows.append([o, f, len(rs), round(float(np.median(wd)), 2), round(float(np.percentile(wd, 10)), 2),
                     round(float(np.percentile(wd, 90)), 2), round(float(np.median(cvs)), 3) if cvs else None,
                     max(trays, key=trays.get), sum(r["human"] for r in rs)])
    rows.sort(key=lambda r: -r[2])
    w("kg_families", ["order", "family", "insects", "width_median_mm", "width_p10_mm", "width_p90_mm",
                      "size_cv_median", "main_tray", "human_steps"], rows)
    rev = sorted([r for r in ins if r["human"]], key=lambda r: ({"STEP-IN": 0, "VIP": 1, "LABEL": 2}[r["decision"]], -r["novelty"]))
    w("kg_review", ["decision", "insect_id", "order", "family", "width_mm", "length_mm", "size_cv", "tray", "why"],
      [[r["decision"], r["insect_id"], r["taxon"].get("order"), r["taxon"].get("family"), r["consensus"]["width_mm"],
        r["consensus"]["length_mm"], r["size_cv"], r["tray"], "; ".join(r["why"])] for r in rev[:300]])
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-kg")
    ap.add_argument("--pseudo", required=True); ap.add_argument("--weights", required=True)
    ap.add_argument("--manifests", nargs="+", required=True)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--limit", type=int); ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)
    graph, lomo, matrix = build(a.pseudo, a.weights, a.manifests, a.repo, a.limit, push=not a.no_push)
    print(json.dumps({"graph_root": graph["graph_root"], "n": graph["n_insects"], "matrix": matrix,
                      "lomo": {m: (v["median_rel_dev"], v["p90_rel_dev"]) for m, v in lomo.items()}}, indent=1))
    print(write_dashboard_csvs(a.repo))


if __name__ == "__main__":
    main()
