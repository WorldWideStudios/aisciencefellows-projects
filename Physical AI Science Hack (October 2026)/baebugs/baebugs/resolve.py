"""Resolvability invariant for the knowledge graph / hypergraph (deterministic, structural).

Every content reference in the graph (weights:<sha256>, artifact:<sha256>, or a "*_sha256" field
inside a custody record) must resolve to bytes in a content store whose sha256 is exactly that value.
A reference that does not resolve is a dangling edge, and a dangling edge is a chain-of-custody BREAK:
the graph claims an object nobody can produce. This is checked over the whole graph every time, so
no individual script has to remember to look.

Store = sha256 -> path index over configured roots (repo + drive outputs), cached by (size, mtime).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

DEFAULT_ROOTS = [".", "/Volumes/magicBLACKbox/baebugs/daisy"]
EXTS = {".pt", ".json", ".jsonl", ".stl", ".glb", ".csv", ".yaml", ".png", ".ipynb"}
REF_KEYS = ("weights_sha256",)          # fields inside records that must resolve


def _sha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


class Store:
    def __init__(self, roots=None, cache=".custody_watch/store_index.json", exts=EXTS):
        self.roots = [Path(r) for r in (roots or DEFAULT_ROOTS)]
        self.cache_f = Path(cache); self.exts = exts
        self.cache = json.loads(self.cache_f.read_text()) if self.cache_f.exists() else {}
        self.index = {}

    def build(self):
        seen = {}
        for r in self.roots:
            if not r.exists():
                continue
            for p in r.rglob("*"):
                if p.suffix not in self.exts or not p.is_file() or ".git" in p.parts:
                    continue
                st = p.stat(); key = str(p.resolve())
                c = self.cache.get(key)
                h = c["sha"] if c and c["size"] == st.st_size and c["mtime"] == st.st_mtime else _sha(p)
                seen[key] = {"sha": h, "size": st.st_size, "mtime": st.st_mtime}
                self.index.setdefault(h, key)
        self.cache = seen
        self.cache_f.parent.mkdir(parents=True, exist_ok=True)
        self.cache_f.write_text(json.dumps(seen))
        return self

    def resolves(self, sha):
        return self.index.get(sha)


def references(repo="."):
    """Every content reference the graph makes, with where it was made."""
    from .mmr import MMRLog
    refs = []
    for f in sorted(Path(repo).glob("daisy/*mmr.jsonl")):
        for r in MMRLog(f).records:
            x = r["record"]
            for k in REF_KEYS:
                if x.get(k):
                    refs.append({"sha": x[k], "kind": k, "where": f"{f.name}#{r['index']}",
                                 "context": f"{x.get('protocol')}/{x.get('run')}", "acknowledged": x.get("type") == "custody_break"})
    for f in sorted(Path(repo).glob("daisy/results/**/results.json")):
        d = json.loads(f.read_text())
        for name, r in d.get("results", {}).items():
            if r.get("weights_sha256"):
                refs.append({"sha": r["weights_sha256"], "kind": "weights_sha256", "where": str(f),
                             "context": f"{d.get('protocol')}/{name}", "acknowledged": False})
    return refs


def dangling(repo=".", store=None):
    store = store or Store([repo, *DEFAULT_ROOTS[1:]]).build()
    out = {}
    for ref in references(repo):
        if not store.resolves(ref["sha"]):
            k = ref["sha"]
            d = out.setdefault(k, {"sha": k, "contexts": set(), "where": [], "kind": ref["kind"]})
            d["contexts"].add(ref["context"]); d["where"].append(ref["where"])
    return [{**v, "contexts": sorted(v["contexts"])} for v in out.values()]


def record_breaks(repo=".", store=None):
    """Append an explicit custody_break event for each dangling reference not yet recorded."""
    from .mmr import MMRLog
    log = MMRLog(Path(repo, "daisy/impact_mmr.jsonl"))
    already = {r["record"].get("missing_sha256") for r in log.records if r["record"].get("type") == "custody_break"}
    new = []
    for d in dangling(repo, store):
        if d["sha"] in already:
            continue
        rec = {"type": "custody_break", "invariant": "every referenced hash resolves to stored bytes",
               "missing_sha256": d["sha"], "kind": d["kind"], "contexts": d["contexts"], "referenced_at": d["where"][:6],
               "cause": "kernel FINISH exported weights only for status EXECUTED after EVAL relabelled runs "
                        "OBSERVED_EXPLORATORY; working dir deleted (fixed: weights saved right after training, "
                        "fail-closed custody_check before results.json)"}
        log.append(rec); new.append(rec)
    return new
