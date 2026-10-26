"""Hybridize break points from several graphs into a new graph with a novel id.

A HYBRID joins parents taken from different graphs: a root or leaf of the toy KG,
a passage test leaf, a hypergraph edge, an impact-MMR event, another hybrid...
Each parent carries an inclusion proof against its own graph's root. The hybrid id
hashes the sorted parents (graph, kind, id, root), the join RULE and the PAYLOAD
(what the combination asserts). Nothing else enters the id, so the hybrid is unique
to that combination and anyone holding the parent graphs can recompute and verify it.
Hybrids are appended to daisy/hybrids_mmr.jsonl and appear in the hypergraph as
`hybrid` hyperedges, so they can be parents of later hybrids.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .explore import merkle_root
from .mmr import MMR, MMRLog

LOG = Path("daisy/hybrids_mmr.jsonl")


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _h(a, b):
    return hashlib.sha256((a + b).encode()).hexdigest()       # same pairing as explore.merkle_root


def merkle_proof(leaves, i):
    """Inclusion proof for explore.merkle_root's construction (odd levels duplicate the last)."""
    level, idx, path = list(leaves), i, []
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        sib = idx ^ 1
        path.append(("L" if sib < idx else "R", level[sib]))
        level = [_h(a, b) for a, b in zip(level[::2], level[1::2])]
        idx //= 2
    return {"type": "merkle", "path": path}


def verify_merkle(leaf, proof, root):
    acc = leaf
    for side, sib in proof["path"]:
        acc = _h(sib, acc) if side == "L" else _h(acc, sib)
    return acc == root


def parent(graph, kind, id_, root, proof=None):
    return {"graph": graph, "kind": kind, "id": id_, "root": root, "proof": proof}


def verify_parent(p):
    if p["proof"] is None:
        return p["kind"] == "root" and p["id"] == p["root"]            # a root stands for itself
    if p["proof"].get("type") == "merkle":
        return verify_merkle(p["id"], p["proof"], p["root"])
    return MMR.verify(p["proof"], p["root"]) and p["proof"]["leaf"] == p["id"]


def hybridize(parents, rule, payload, log_path=LOG, record=True):
    bad = [p["id"][:12] for p in parents if not verify_parent(p)]
    if bad:
        raise ValueError(f"parent proofs fail: {bad}")
    core = {"type": "hybrid", "rule": rule, "payload": payload,
            "parents": sorted(({k: p[k] for k in ("graph", "kind", "id", "root")} for p in parents),
                              key=lambda x: (x["graph"], x["id"]))}
    hyb = {**core, "id": H(core), "proofs": {p["id"]: p["proof"] for p in parents}}
    if record:
        MMRLog(log_path).append(hyb)
    return hyb


def verify_hybrid(h):
    core = {k: h[k] for k in ("type", "rule", "payload", "parents")}
    if H(core) != h["id"]:
        return False, "id"
    for p in h["parents"]:
        if not verify_parent({**p, "proof": h["proofs"].get(p["id"])}):
            return False, p["id"][:12]
    return True, None


# --------------------------------------------------------- graph accessors

def mmr_parent(path, index, graph):
    log = MMRLog(path)
    return parent(graph, "leaf", log.records[index]["leaf"], log.mmr.root, log.mmr.proof(index)), log.records[index]["record"]


def hypergraph_edge_parent(edge_hash, repo="."):
    from .hypergraph import build
    g = build(repo)
    leaves = sorted(e["hash"] for e in g["edges"])
    return parent("hypergraph", "edge", edge_hash, merkle_root(leaves), merkle_proof(leaves, leaves.index(edge_hash))), g


def truth_subject_parent(toy, truth_path="daisy/TRUTH-001.json"):
    from .address import H as AH
    t = json.loads(Path(truth_path).read_text())
    leaves = sorted(AH(s) for s in t["subjects"])
    s = next(x for x in t["subjects"] if x["toy"] == toy)
    leaf = AH(s)
    return parent("truth:" + t["id"][:16], "leaf", leaf, t["subjects_root"], merkle_proof(leaves, leaves.index(leaf))), s


def passage_parent(toy, hole, mode="body_folded", root_dir="print/filters/passage"):
    edges = [json.loads(l) for l in Path(root_dir, mode, "edges.jsonl").read_text().splitlines() if l.strip()]
    summ = json.loads(Path(root_dir, mode, "summary.json").read_text())
    leaves = sorted(e["leaf"] for e in edges)
    e = next(x for x in edges if x["insect"] == toy and x["hole"] == hole)
    return parent(f"passage:{mode}", "leaf", e["leaf"], summ["passage_root"], merkle_proof(leaves, leaves.index(e["leaf"]))), e
