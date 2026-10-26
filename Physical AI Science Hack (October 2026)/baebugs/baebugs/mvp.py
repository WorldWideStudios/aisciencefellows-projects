"""The MVP graph pack: one JSON that every surface reads (web page, CLI, MCP, npx), so all of them give the
same root for the same tree.

Levels (root -> leaf), every node with an address:
  root                 mvp root = Merkle(aok root, hypergraph root, every MMR log root)
  module:<name>        AoK module root (code, prints, labware, results, ...)
  leaf:<path>          one tracked file: sha256, claim, licence in context, status, leaf hash
  bug / species / part / labware / result views point at their leaf by path

  python -m baebugs.mvp            -> site/mvp/mvp.json
  python -m baebugs.mvp get <address|path|text>
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from . import aok as aokm
from .explore import merkle_root
from .mmr import MMRLog

OUT = "site/mvp/mvp.json"


def _mmr_roots(repo):
    out = {}
    for f in sorted(Path(repo, "daisy").glob("*mmr.jsonl")):
        log = MMRLog(f)
        ok, _bad = log.verify()
        out[f.stem] = {"root": log.records[-1]["root"] if log.records else None, "n": len(log.records), "verified": ok}
    return out


def _species(repo, leaf_of):
    groups = defaultdict(list)
    p = Path(repo, "kg/insects.jsonl")
    if not p.exists():
        return []
    for line in p.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line); t = r.get("taxon", {})
        L = (r.get("sizes", {}).get("teacher") or {}).get("length_mm")
        groups[(t.get("order") or "?", t.get("family") or "?", t.get("scientificName") or "?")].append(
            (L, (t.get("license") or "").split("/licenses/")[-1].split("/publicdomain/")[-1].strip("/"), t.get("institutionCode")))
    out = []
    for (o, f, s), xs in sorted(groups.items()):
        Ls = [x[0] for x in xs if x[0]]
        out.append({"order": o, "family": f, "species": s, "n": len(xs),
                    "length_mm_median": round(statistics.median(Ls), 1) if Ls else None,
                    "licences": sorted({x[1] for x in xs if x[1]}), "collections": sorted({x[2] for x in xs if x[2]}),
                    "path": "kg/insects.jsonl", "leaf": leaf_of.get("kg/insects.jsonl")})
    return out


def _assets(repo):
    p = Path(repo, "kg/assets.json")
    if not p.exists():
        return {"root": None, "items": []}
    db = json.loads(p.read_text())
    photos = {x["photo_id"]: x for x in json.loads(Path(repo, "assets/photos.json").read_text())}
    return {"root": db["root"], "photos_root": db["photos_root"], "dims_by_source": db["dims_by_source"],
            "items": [{k: a.get(k) for k in ("id", "name", "category", "maker", "ref", "count", "role", "interfaces",
                                             "dims_mm", "dims_source", "notes", "leaf")}
                      | {"photos": [photos[ph].get("file") for ph in a["photos"] if photos[ph].get("file")]}
                      for a in db["assets"]]}


def build(repo="."):
    repo = Path(repo)
    A = aokm.build(repo)
    leaf_of = {x["path"]: x["leaf"] for x in A["leaves"]}
    hg = json.loads(Path(repo, "daisy/hypergraph.json").read_text())
    mmr = _mmr_roots(repo)
    bugs = []
    man = Path(repo, "print/fuse1/manifest.csv")
    if man.exists():
        for r in csv.DictReader(man.open()):
            path = f"print/fuse1/{r['file']}"
            bugs.append({"order": r["order"], "family": r["family"], "level": r["level"], "group": r["group"],
                         "length_mm": float(r["length_mm"]), "kit_tray": r["kit_tray"], "size_flag": r["size_flag"],
                         "representation": r["representation"], "path": path, "leaf": leaf_of.get(path)})
    lab = json.loads(Path(repo, "site/lab/parts.json").read_text())
    parts = [{"name": p["name"], "modules": p["modules"], "platform": p["platform"], "status": p["status"],
              "materials": p["materials"], "stages": p.get("stages", []), "bbox_mm": p["bbox_mm"],
              "path": "site/" + p["stl"], "leaf": leaf_of.get("site/" + p["stl"]), "sha256": p["sha256"]}
             for p in lab["parts"]]
    ot = json.loads(Path(repo, "opentrons/parts.json").read_text())
    labware = [{"name": p["part"], "path": "opentrons/" + p["stl"], "leaf": leaf_of.get("opentrons/" + p["stl"]),
                "bbox_mm": p["bbox_mm"], "sha256": p["sha256"]} for p in ot["parts"]]
    remixes = []                                                       # labware twin: printable SBS/cryo remixes
    cat = Path(repo, "print/labware/catalog.json")
    if cat.exists():
        c = json.loads(cat.read_text())
        for x in c["prints"]:
            m, stl = c["print_meta"].get(x["id"], {}), f"print/labware/stl/{x['id']}.stl"
            ot = "print/labware/opentrons/baebugs_" + x["id"].removeprefix("print-").replace("-", "_") + ".json"
            remixes.append({"name": x["name"], "id": x["id"], "material": x.get("material"), "licence": x.get("license"),
                            "bbox_mm": m.get("bbox"), "grams": m.get("grams"), "usd": m.get("usd"),
                            "path": stl, "leaf": leaf_of.get(stl), "opentrons": ot if Path(repo, ot).exists() else None})
    breaks = [r["record"] for r in MMRLog(Path(repo, "daisy/impact_mmr.jsonl")).records if r["record"].get("type") == "custody_break"]
    missing = {b.get("missing_sha256") for b in breaks}
    photo_breaks = Path(repo, "print/labware/merkle/breaks.json")      # labware twin: source photos withheld (vendor marks)
    photo_breaks = json.loads(photo_breaks.read_text()) if photo_breaks.exists() else []
    bench_photo_note = Path(repo, "docs/bench/bench_photo_observation_20261025.json")
    withheld_bench_sources = []
    if bench_photo_note.exists():
        bench_note = json.loads(bench_photo_note.read_text())
        source = bench_note["source"]
        if source["public_source_bytes"] != "PUBLISHED":
            withheld_bench_sources.append({
                "record_path": "docs/bench/bench_photo_observation_20261025.json",
                "source_sha256": source["sha256_exact_file_bytes"],
                "reason": "source bytes withheld; distribution consent/rights UNKNOWN",
                "public_rehash": "NOT_AVAILABLE"
            })

    results = []
    for f in sorted(Path(repo, "daisy/results").rglob("results.json")):
        d = json.loads(f.read_text()); rel = str(f.relative_to(repo))
        runs = d.get("results", {})
        results.append({"protocol": d.get("protocol"), "path": rel, "leaf": leaf_of.get(rel), "runs": len(runs),
                        "custody": "BROKEN (weights not stored)" if any(
                            r.get("weights_sha256") in missing for r in runs.values()) else "NO WEIGHTS (runs failed)" if not any(
                            r.get("weights_sha256") for r in runs.values()) else (d.get("custody_status") or "INTACT"),
                        "statuses": sorted({r.get("status") for r in runs.values()} - {None})})
    roots = {"aok": A["root"], "hypergraph": hg["root"], **{k: v["root"] for k, v in mmr.items()}}
    if Path(repo, "kg/assets.json").exists():
        roots["assets"] = json.loads(Path(repo, "kg/assets.json").read_text())["root"]
    root = merkle_root(sorted(v for v in roots.values() if v))
    return {"type": "baebugs-mvp", "root": root, "roots": roots, "mmr": mmr,
            "custody": {"breaks": len(breaks) + len(photo_breaks) + len(withheld_bench_sources), "result_breaks": len(breaks),
                        "withheld_photo_breaks": len(photo_breaks),
                        "withheld_bench_sources": withheld_bench_sources,
                        "break_contexts": sorted({c for b in breaks for c in b.get("contexts", [])}),
                        "rule": "every hash the graph references must resolve to stored bytes; otherwise BREAK"},
            "legend": A["legend"], "totals": A["totals"], "modules": A["modules"], "external": A["external"],
            "leaves": [{k: x[k] for k in ("path", "module", "kind", "claim", "licence", "status", "sha256", "leaf")}
                       for x in A["leaves"]],
            "bugs": bugs, "species": _species(repo, leaf_of), "parts": parts, "labware": labware, "remixes": remixes, "results": results,
            "assets": _assets(repo),
            "repo": "https://github.com/biobitworks/baebugs"}


def get(pack, q):
    """Resolve an address (root, module:<name>, leaf:<path>, a leaf hash, a sha256) or a path, else search text."""
    q = q.strip()
    if q in ("root", pack["root"]):
        return {"address": "root", "root": pack["root"], "roots": pack["roots"]}
    if q.startswith("module:") and q[7:] in pack["modules"]:
        m = q[7:]
        return {"address": q, **pack["modules"][m], "leaves": [x["path"] for x in pack["leaves"] if x["module"] == m]}
    key = q.removeprefix("leaf:")
    for x in pack["leaves"]:
        if key in (x["path"], x["leaf"], x["sha256"]):
            return {"address": f"leaf:{x['path']}", **x}
    for e in pack["external"]:
        if q in (e["id"], e["leaf"]):
            return {"address": e["id"], **e}
    ql = q.lower()
    hits = [f"leaf:{x['path']}" for x in pack["leaves"] if ql in json.dumps(x).lower()]
    return {"query": q, "hits": hits[:50], "n": len(hits)}


def prove(pack, fco):
    """Compare someone's FCO/FCG ({"leaves":[{"path","sha256"}]}) with the graph -> attestation (same as the web page)."""
    by = {x["path"]: x for x in pack["leaves"]}
    rows = []
    for leaf in fco.get("leaves", []):
        x = by.get(leaf.get("path"))
        v = "NOT IN GRAPH" if not x else "MATCH" if leaf.get("sha256") == x["sha256"] else "DIFFERS"
        rows.append({"path": leaf.get("path"), "yours": leaf.get("sha256"), "graph": x["sha256"] if x else None, "verdict": v})
    return {"type": "baebugs-attestation", "graph_root": pack["root"], "compared": len(rows),
            "match": sum(r["verdict"] == "MATCH" for r in rows), "rows": rows}


def fco_of(paths, repo="."):
    """Make your own FCO from files you have (BYO): path + sha256 per leaf."""
    return {"type": "fco", "leaves": [{"path": p, "sha256": aokm._sha(Path(repo, p))} for p in paths]}


RAW = "https://raw.githubusercontent.com/biobitworks/baebugs/main/site/mvp/mvp.json"


def load(path=None):
    """The graph pack: an explicit path, else the repo checkout, else ./site/mvp, else the published copy on main."""
    for p in ([Path(path)] if path else []) + [Path(__file__).resolve().parents[1] / OUT, Path(OUT)]:
        if p.exists():
            return json.loads(p.read_text())
    import urllib.request
    with urllib.request.urlopen(RAW, timeout=30) as r:
        return json.loads(r.read())


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "prove":
        print(json.dumps(prove(load(), json.loads(Path(argv[1]).read_text())), indent=1))
        return 0
    if argv and argv[0] == "compare":
        from .compare import compare
        other = json.loads(Path(argv[1]).read_text())
        print(json.dumps(compare(load(argv[2]) if len(argv) > 2 else load(), other, "claude", "byo"), indent=1))
        return 0
    if argv and argv[0] == "fco":
        print(json.dumps(fco_of(argv[1:]), indent=1))
        return 0
    if argv and argv[0] == "get":
        pack = load()
        print(json.dumps(get(pack, " ".join(argv[1:]) or "root"), indent=1))
        return 0
    pack = build(".")
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(json.dumps(pack, indent=0, sort_keys=True) + "\n")
    print(json.dumps({"root": pack["root"], "leaves": len(pack["leaves"]), "bugs": len(pack["bugs"]),
                      "species": len(pack["species"]), "parts": len(pack["parts"]), "custody_breaks": pack["custody"]["breaks"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
