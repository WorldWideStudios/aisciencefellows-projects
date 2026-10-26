"""Protocol Board: a pin-board front end over the baebugs graph.

Every card is something a scientist can save, run step by step, remix or contest: preregistered protocols, results,
print packages, bench objects and escalation-ladder steps. Cards carry their Merkle address, so a pinned card always
points at the exact bytes in the repo. Data and thumbnails are embedded, so the page works as a single file.

  python -m baebugs.board    -> site/board/index.html (+ a skeleton-free copy for the artifact viewer)
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path

REPO_URL = "https://github.com/biobitworks/baebugs"


def thumb(path, w=420):
    from PIL import Image
    p = Path(path)
    if not p.exists():
        return None
    im = Image.open(p).convert("RGB"); im.thumbnail((w, w * 2))
    b = io.BytesIO(); im.save(b, "JPEG", quality=68, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()


def short(h):
    return (h or "")[:12]


def protocol_cards(repo):
    out = []
    dec = {"DAISY-BB-002a": "daisy/results/DAISY-BB-002a/v2/DECISION.md", "DAISY-BB-004": "daisy/results/DAISY-BB-004/v4/DECISION.md",
           "DAISY-BB-001b": "daisy/results/DAISY-BB-001b/v6/DECISION.md"}
    blurbs = {
        "DAISY-BB-001b": ("Synthetic, pseudo-labelled and multi-resolution training for specimen segmentation; leave-one-out runs.",
                          "Ran 6 runs; weights never stored, so 6 custody breaks are on record. Exploratory only.", "BROKEN"),
        "DAISY-BB-002a": ("Do real California museum photos beat synthetic-only training on other states?",
                          "Yes on AZ (+0.696) and OR (+0.521) mask mAP50-95. NV too small to read.", "SUPPORTED"),
        "DAISY-BB-004": ("Per-taxon preprocessors: an insect-order router plus family models for the two biggest orders.",
                         "Order router USEFUL (test macro-F1 0.70 vs 0.14). Hymenoptera family NULL out of state. Diptera undecided.", "USEFUL"),
    }
    gate_words = {"G0": "Check the frozen protocol hash", "G1": "Re-hash every data file against the frozen Merkle root",
                  "G2": "Check the starting weights against the pinned hash", "G3a": "Record the software environment",
                  "G3b": "Smoke-train with and without mixed precision", "G3c": "Stop a run at the first non-finite epoch",
                  "values_epoch": "Check every epoch's loss is finite", "custody_check": "Every weights hash must resolve to stored bytes",
                  "smoke_fraction": "Use a small fraction for the smoke test"}
    for pid, (q, res, verdict) in blurbs.items():
        f = Path(repo, f"daisy/{pid}.json")
        if not f.exists():
            continue
        P = json.loads(f.read_text())
        S = P.get("settings", {})
        steps = [{"t": f"{k}: {gate_words.get(k, k)}"} for k in P.get("gates", {})]
        steps += [{"t": f"Train {r['name']} ({S.get('epochs', '?')} epochs, imgsz {S.get('imgsz', '?')})", "min": None} for r in P.get("runs", [])]
        steps += [{"t": "Evaluate on held-out states with the frozen decision rule"}, {"t": "Write results, events root and custody status"}]
        out.append({"id": pid, "type": "protocol", "title": pid, "lede": q, "result": res, "status": verdict,
                    "tags": ["DAISY", "preregistered", f"{len(P.get('runs', []))} runs"],
                    "hash": hashlib.sha256(f.read_bytes()).hexdigest(), "path": f"daisy/{pid}.json",
                    "more": dec.get(pid), "steps": steps})
    return out


def print_cards(repo):
    cards = []
    specs = [
        ("trommel_biokea_split", "Trommel for BioKEA trays, split", "Drum zones on the Fuse 1+, caps, stands and crank on one X1 Carbon plate. Fits the BioKEA trays.",
         "print/packages/trommel_biokea_split/manifest.json", "print/packages/trommel_biokea_x1c/plate_preview.png", "READY",
         ["Print the 3 drum zones on the Fuse 1+ (fuse1_zones_build.stl)", "Depowder the zones in the Fuse Sift",
          "Print caps, stands and crank on the X1C (x1c_rest_plate.stl)", "Check the 608 bearing and 8 mm rod fits on the stands",
          "Press bearings into both stands; taller stand at the inlet", "Slide on inlet cap, 2 mm, 4 mm, 7 mm zones, outlet cap",
          "Rod through bearings, crank on, lock the set screws", "Slide three BioKEA trays under the zones and turn slowly"]),
        ("trommel_biokea_x1c", "Trommel, one X1 Carbon plate", "All 8 parts on one 256 mm plate. FDM attempt 1 failed on the perforated zones.",
         "print/packages/trommel_biokea_x1c/manifest.json", "print/packages/trommel_biokea_x1c/plate_preview.png", "RETRY",
         ["Dry the filament", "Print one zone alone first with a brim, outer walls 40-60 mm/s", "If it holds, print the full plate"]),
        ("pa12_toys", "Printed toy insects, 91 sizes", "Parametric PA12 toys sized from museum statistics: size standards for the sieve and vision lanes.",
         "print/fuse1/manifest.csv", "assets/photos/pa12_toys_box.jpg", "PRINTED",
         ["Pick off any FDM strings", "Lay 10-20 toys flat on a plain tray", "Put the ruler in frame", "Shoot straight down",
          "Run the escalation ladder on the photos"]),
    ]
    for cid, title, lede, path, img, status, steps in specs:
        p = Path(repo, path)
        cards.append({"id": cid, "type": "print", "title": title, "lede": lede, "status": status, "img": thumb(Path(repo, img)),
                      "tags": ["3D print", "MIT"], "hash": hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None,
                      "path": path, "steps": [{"t": s} for s in steps]})
    return cards


def asset_cards(repo):
    db = json.loads(Path(repo, "kg/assets.json").read_text())
    photos = {p["photo_id"]: p for p in json.loads(Path(repo, "assets/photos.json").read_text())}
    out = []
    for a in db["assets"]:
        ph = next((photos[x] for x in a["photos"] if photos.get(x, {}).get("file", "").endswith(".jpg")), None)
        dims = a.get("dims_mm")
        out.append({"id": a["id"], "type": "bench", "title": a["name"], "lede": a.get("role") or "",
                    "status": a.get("status") or a["dims_source"].upper(), "img": thumb(Path(repo, ph["file"])) if ph else None,
                    "tags": [t for t in [a["category"], a.get("maker"), *(a.get("interfaces") or [])[:2]] if t],
                    "dims": " x ".join("?" if v is None else f"{v:g}" for v in dims) + " mm" if dims else None,
                    "hash": a["leaf"], "path": "kg/assets.json", "steps": []})
    return out


def ladder_cards(repo):
    rows = json.loads(Path(repo, "docs/ladder_demo/rows.json").read_text())
    out = []
    for i, r in enumerate(rows[:10]):
        snap = Path(repo, f"docs/ladder_demo/snapshots/{i:02d}_{r['step']}.png")
        ok = "correct" if r.get("label") == r["truth_order"] else ("not a taxon call" if r["decided_by"] in ("check:frame-diff", "human") else "wrong")
        taxon = r["decided_by"].startswith(("taxon:", "local:"))
        lede = (f"Decided by {r['decided_by']}: {r['outcome']}. Truth {r['truth_order']}, called {r.get('label') or '-'} ({ok})." if taxon
                else f"Decided by {r['decided_by']}: {r['outcome']}. {r.get('label') or ''}".strip())
        out.append({"id": f"ladder_{i}", "type": "ladder", "title": f"{r['toy'].split('_')[0]} at {r['step']}", "lede": lede,
                    "status": r["outcome"], "img": thumb(snap) if snap.exists() else None,
                    "tags": ["escalation", r["decided_by"].split(":")[0], f"novelty {r['novelty']}"], "hash": r["leaf"],
                    "path": "docs/ladder_demo/ladder_mmr.jsonl",
                    "steps": [{"t": "Taxon model (in scope, confident, not too novel?)"}, {"t": "Local vision model"},
                              {"t": "Claude"}, {"t": "Human entomologist"}]})
    return out


def build(repo="."):
    cards = protocol_cards(repo) + print_cards(repo) + ladder_cards(repo) + asset_cards(repo)
    mvp = json.loads(Path(repo, "site/mvp/mvp.json").read_text())
    return {"root": mvp["root"], "cards": cards}


def render(data, full_doc):
    tpl = Path(__file__).with_name("board_template.html").read_text()
    mk = Path(__file__).resolve().parents[1] / "assets/brand/baebugs_mark.svg"
    mkd = mk.with_name("baebugs_mark_dark.svg")
    tpl = tpl.replace("/*__MARK__*/", mk.read_text().strip() if mk.exists() else "")
    tpl = tpl.replace("/*__MARKDARK__*/", mkd.read_text().strip() if mkd.exists() else "")
    html = tpl.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"))).replace("__REPO__", REPO_URL)
    if full_doc:
        html = ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + html.replace("<!--BODY-->", "</head>\n<body>", 1)
                + "\n</body>\n</html>\n")
    else:
        html = html.replace("<!--BODY-->", "", 1)
    return html


def main(repo=".", out="site/board/index.html", artifact=None):
    data = build(repo)
    Path(repo, out).parent.mkdir(parents=True, exist_ok=True)
    Path(repo, out).write_text(render(data, True))
    if artifact:
        Path(artifact).write_text(render(data, False))
    print(json.dumps({"cards": len(data["cards"]), "bytes": len(render(data, True))}))


if __name__ == "__main__":
    import sys
    main(artifact=sys.argv[1] if len(sys.argv) > 1 else None)
