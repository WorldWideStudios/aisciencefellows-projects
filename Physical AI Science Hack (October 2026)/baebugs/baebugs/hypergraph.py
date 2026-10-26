"""Connected hypergraphs over every chain-of-custody structure in the repo.

Nodes are content addresses (truth, dataset member roots, protocol runs/recipes,
toys, actors, values/policies, weights, ledger roots). Hyperedges join many nodes
at once and are themselves hashed:

  custody     dataset member  <- files root, lineage parents          (daisy/datasets.json)
  recipe      protocol run    <- train/val member roots, settings, gates (daisy/DAISY-BB-*.json)
  amendment   protocol        <- parent protocol sha + reason
  toy         insect hash     <- collection root (toy Merkle KG)
  evaluation  MMR event       <- truth, actor, values, weights, attestation root
  consensus   MMR event       <- truth, values, all actors
  execution   MMR event       <- protocol, platform, status
  ledger      ledger file     <- leaf root (git break points)

hypergraph root = Merkle root over sorted hyperedge hashes; snapshots are appended
to daisy/hypergraph_mmr.jsonl, so every past state of the whole web is provable.

LOMO on the hypergraph: remove one node (here: one actor) and recompute what depends
on it (consensus per claim). Flips = that node's influence; no flips = redundant.
"""
from __future__ import annotations

import json
from pathlib import Path

from .address import H
from .explore import merkle_root
from .mmr import MMRLog


def _edge(kind, nodes, data=None):
    body = {"kind": kind, "nodes": sorted({n for n in nodes if n}), "data": data or {}}
    return {**body, "hash": H(body)}


def build(repo="."):
    R = Path(repo)
    edges = []
    ds = json.loads((R / "daisy/datasets.json").read_text())
    edges.append(_edge("datasets_root", [f"datasets_root:{ds['root']}", *[f"dataset:{n}" for n in ds["datasets"]]],
                       {"members": len(ds["datasets"])}))
    for name, d in ds["datasets"].items():
        parents = [f"dataset:{p}" for p in (d.get("derived_from") or [])]
        edges.append(_edge("custody", [f"dataset:{name}", f"root:{d.get('merkle_root')}", *parents],
                           {"status": d.get("status"), "files": d.get("files"), "_name": name}))
    for pf in sorted(R.glob("daisy/DAISY-BB-*.json")):
        P = json.loads(pf.read_text())
        pid = f"protocol:{P['id']}"
        if P.get("amends"):
            edges.append(_edge("amendment", [pid, f"protocol:{P['amends']['protocol']}"],
                               {"reason": P["amends"]["reason"][:160]}))
        for run in P["runs"]:
            members = run.get("train", []) + run.get("val", [])
            data_nodes = ([f"dataset:{P['bundle']}", f"root:{P['data_root']}"] if P.get("data_root") else [])
            edges.append(_edge("recipe", [pid, f"run:{P['id']}:{run['name']}", *data_nodes,
                                          *[f"dataset:{m}" for m in members],
                                          *[f"root:{P.get('roots', {}).get(m)}" for m in members]],
                               {"settings": {k: v for k, v in P["settings"].items() if k != "workers"}}))
    truth = json.loads((R / "daisy/TRUTH-001.json").read_text())
    tnode = f"truth:{truth['id']}"
    edges.append(_edge("truth", [tnode, f"kgroot:{truth['sources']['toy_kg_collection_root']}",
                                 f"datasets_root:{truth['sources']['daisy_datasets_root']}"]))
    for s in truth["subjects"]:
        edges.append(_edge("toy", [tnode, f"toy:{s['insect_hash']}", f"name:{s['toy']}", f"subject:{H(s)}"], {"plan": s["plan"]}))
    log = MMRLog(R / "daisy/impact_mmr.jsonl")
    for r in log.records:
        x = r["record"]
        if x["type"] == "evaluation":
            edges.append(_edge("evaluation", [tnode, f"actor:{x['actor']['id']}", f"values:{x['values']}",
                                              f"weights:{H(x.get('weights'))}", f"att:{x['attestation_root']}",
                                              f"mmr:{r['leaf']}"], {"actor": x["actor"]["name"], "pass": x["pass"], "n": x["n"]}))
        elif x["type"] == "consensus":
            edges.append(_edge("consensus", [tnode, f"values:{x['values']}", *[f"actor:{a}" for a in x["actors"]],
                                             f"mmr:{r['leaf']}"], {"status_counts": x["status_counts"]}))
        elif x["type"] == "execution":
            why = x.get("reason") or x.get("root_cause") or x.get("note") or x.get("error")
            nodes = [f"protocol:{x['protocol']}", f"mmr:{r['leaf']}"] + ([f"run:{x['protocol']}/{x['run']}"] if x.get("run") else []) \
                + ([f"weights:{x['weights_sha256']}"] if x.get("weights_sha256") else [])
            edges.append(_edge("execution", nodes, {"status": x["status"], "reason": why}))
    hl = R / "daisy/hybrids_mmr.jsonl"
    if hl.exists():
        for r in MMRLog(hl).records:
            h = r["record"]
            edges.append(_edge("hybrid", [f"hybrid:{h['id']}", *[f"{p['graph']}:{p['id']}" for p in h["parents"]],
                                          *[_alias(p) for p in h["parents"]]], {"rule": h["rule"]}))
    for lf in sorted((R / "ledger").glob("*.jsonl")):
        recs = [json.loads(l) for l in lf.read_text().splitlines() if l.strip()]
        if recs:
            edges.append(_edge("ledger", [f"ledger:{lf.stem}", f"ledgerroot:{recs[-1].get('root')}"], {"leaves": len(recs)}))
    for e in edges:                                   # every hyperedge is addressable as a node
        e["nodes"] = sorted(set(e["nodes"]) | {f"edge:{e['hash']}"})
    nodes = sorted({n for e in edges for n in e["nodes"]})
    root = merkle_root(sorted(e["hash"] for e in edges))
    return {"root": root, "edges": edges, "nodes": nodes,
            "counts": {k: sum(e["kind"] == k for e in edges) for k in sorted({e["kind"] for e in edges})}}


def _alias(p):
    """Map a hybrid parent onto the node naming used elsewhere in the hypergraph."""
    g, i = p["graph"], p["id"]
    if g == "impact_mmr":
        return f"mmr:{i}"
    if g == "hypergraph":
        return f"edge:{i}"
    if g.startswith("truth:"):
        return f"subject:{i}"
    return f"{g}:{i}"


def neighbours(graph, node):
    return [e for e in graph["edges"] if node in e["nodes"]]


def walk_to_truth(graph, node, max_hops=6):
    """Breadth-first path of hyperedges from any node to the frozen truth."""
    from collections import deque
    q, seen = deque([(node, [])]), {node}
    while q:
        n, path = q.popleft()
        if n.startswith("truth:"):
            return path
        if len(path) >= max_hops:
            continue
        for e in neighbours(graph, n):
            for m in e["nodes"]:
                if m not in seen:
                    seen.add(m); q.append((m, path + [(e["kind"], e["hash"][:12], m)]))
    return None


def lomo_actors(repo=".", values="exact", quorum=0.5):
    """Leave-one-actor-out on consensus: recompute each claim's status without one
    actor; flips measure that actor's influence. Reference (code) actor = logic-twin."""
    log = MMRLog(Path(repo) / "daisy/impact_mmr.jsonl")
    ev = [r["record"] for r in log.records if r["record"].get("type") == "evaluation" and r["record"]["values"] == values
          and r["record"].get("passed")]
    if not ev:
        return {}
    ref = next((e for e in ev if e["actor"]["name"] == "logic-twin"), None)
    agents = [e for e in ev if e is not ref]
    toys = sorted(ev[0]["passed"])

    def status(toy, use):
        if ref and not ref["passed"].get(toy):
            return "FAILED"
        if not use:
            return "UNKNOWN"
        agree = sum(e["passed"].get(toy, False) for e in use) / len(use)
        return "SUPPORTED" if agree >= quorum else "DISPUTED"

    full = {t: status(t, agents) for t in toys}
    out = {}
    for a in agents:
        rest = [e for e in agents if e is not a]
        flips = [t for t in toys if status(t, rest) != full[t]]
        out[a["actor"]["name"]] = {"flips": len(flips), "examples": flips[:4]}
    return {"values": values, "baseline": {s: list(full.values()).count(s) for s in set(full.values())},
            "leave_one_actor_out": dict(sorted(out.items(), key=lambda kv: -kv[1]["flips"]))}


def snapshot(repo=".", ledger=False):
    g = build(repo)
    log = MMRLog(Path(repo) / "daisy/hypergraph_mmr.jsonl")
    if not log.records or log.records[-1]["record"]["root"] != g["root"]:
        log.append({"type": "hypergraph_snapshot", "root": g["root"], "counts": g["counts"], "nodes": len(g["nodes"])})
    Path(repo, "daisy/hypergraph.json").write_text(json.dumps({k: g[k] for k in ("root", "counts", "nodes", "edges")}, indent=1))
    if ledger:
        from .git_ledger import GitLedger
        GitLedger("hypergraph", repo).append("snapshot", {"root": g["root"], "counts": g["counts"], "mmr_root": log.mmr.root},
                                             files={"hypergraph": Path(repo, "daisy/hypergraph.json")})
    return g, log


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", action="store_true")
    a = ap.parse_args()
    g, log = snapshot(".", a.ledger)
    print("hypergraph root", g["root"][:16], g["counts"], "nodes", len(g["nodes"]), "| snapshots", len(log.records))
    for v in ("exact", "tol_0.5mm", "plan_only"):
        print(json.dumps(lomo_actors(".", v))[:900])


# ------------------------------------------------- LOMO over the hypergraph
# Each hyperedge kind declares which of its nodes are OUTPUTS (produced by it); all
# other nodes are inputs. Removing a node or an edge invalidates the forward closure.
OUTPUT_PREFIX = {"custody": ("dataset:",), "datasets_root": ("datasets_root:",), "truth": ("truth:",),
                 "toy": ("toy:", "name:", "subject:"), "recipe": ("run:",), "amendment": (),
                 "evaluation": ("att:", "mmr:"), "consensus": ("mmr:",), "execution": ("mmr:",),
                 "hybrid": ("hybrid:",), "ledger": ("ledgerroot:",)}
MODULES = {"insect_lomo": lambda a: a == "logic-twin",
           "model_compare.text": lambda a: a.startswith(("qwen", "lfm")),
           "model_compare.vision": lambda a: a.split("@")[0] in ("classical", "yolo", "yoloe"),
           "toy_triage": lambda a: a.startswith("toy-triage:")}


def _io(e):
    pre = OUTPUT_PREFIX.get(e["kind"], ())
    if e["kind"] == "amendment":          # amendment: parent protocol -> child protocol (the one with the suffix)
        ps = sorted(n for n in e["nodes"] if n.startswith("protocol:"))
        outs = {ps[-1]} if ps else set()
    elif e["kind"] == "custody":
        outs = {f"dataset:{e['data']['_name']}"}
    else:
        outs = {n for n in e["nodes"] if n.startswith(pre)} if pre else set()
    outs |= {f"edge:{e['hash']}"}
    return set(e["nodes"]) - outs, outs


def invalidated(graph, removed_nodes=(), removed_edges=()):
    """Forward closure: an edge is invalid if it was removed or any of its inputs is invalid."""
    bad_nodes, bad_edges = set(removed_nodes), set(removed_edges)
    io = {e["hash"]: _io(e) for e in graph["edges"]}
    changed = True
    while changed:
        changed = False
        for e in graph["edges"]:
            if e["hash"] in bad_edges:
                new = io[e["hash"]][1] - bad_nodes
            elif io[e["hash"]][0] & bad_nodes:
                bad_edges.add(e["hash"]); new = io[e["hash"]][1] - bad_nodes
            else:
                continue
            if new:
                bad_nodes |= new; changed = True
    by = {}
    for e in graph["edges"]:
        if e["hash"] in bad_edges:
            by[e["kind"]] = by.get(e["kind"], 0) + 1
    return {"edges": len(bad_edges), "by_kind": by}


def lomo_graph(repo="."):
    g = build(repo)
    actors = {}
    for e in g["edges"]:
        if e["kind"] == "evaluation":
            a = next(n for n in e["nodes"] if n.startswith("actor:"))
            actors.setdefault(e["data"]["actor"], a)
    out = {"root": g["root"], "module": {}, "merkle": {}, "custody_break": {}}
    # leave one MODULE out: remove its actors -> invalidated evaluations/consensus/hybrids + consensus flips
    for mod, match in MODULES.items():
        nodes = [a for name, a in actors.items() if match(name)]
        if not nodes:
            continue
        inv = invalidated(g, removed_nodes=nodes)
        names = [n for n in actors if match(n)]
        flips = {}
        for v in ("exact", "tol_0.5mm", "plan_only"):
            r = lomo_actors_set(repo, v, exclude=set(names))
            if r:
                flips[v] = r
        out["module"][mod] = {"actors": len(nodes), "invalidated": inv, "consensus_after": flips}
    # leave one MERKLE out: each dataset member root, the toy-KG root, each protocol, the truth
    merkles = [n for n in g["nodes"] if n.startswith(("dataset:", "kgroot:", "protocol:", "truth:"))]
    for n in merkles:
        out["merkle"][n.split(":", 1)[0] + ":" + n.split(":", 1)[1][:28]] = invalidated(g, removed_nodes=[n])
    # leave one CUSTODY BREAK out: each break-point edge
    for e in g["edges"]:
        if e["kind"] in ("amendment", "execution", "datasets_root", "truth", "hybrid", "custody"):
            label = f"{e['kind']}:{e['hash'][:10]}" + (f" ({e['data'].get('rule', '')[:40]})" if e["kind"] == "hybrid" else "")
            out["custody_break"][label] = invalidated(g, removed_edges=[e["hash"]])
    return out


def lomo_actors_set(repo, values, exclude, quorum=0.5):
    """Consensus status counts with a set of actors removed (module-level LOMO)."""
    log = MMRLog(Path(repo) / "daisy/impact_mmr.jsonl")
    ev = [r["record"] for r in log.records if r["record"].get("type") == "evaluation" and r["record"]["values"] == values
          and r["record"].get("passed")]
    if not ev:
        return None
    ref = next((e for e in ev if e["actor"]["name"] == "logic-twin"), None)
    if ref and "logic-twin" in exclude:
        ref = None
    agents = [e for e in ev if e["actor"]["name"] != "logic-twin" and e["actor"]["name"] not in exclude]
    counts = {}
    for t in sorted(ev[0]["passed"]):
        if ref is not None and not ref["passed"].get(t):
            s = "FAILED"
        elif not agents:
            s = "UNKNOWN"
        else:
            s = "SUPPORTED" if sum(e["passed"].get(t, False) for e in agents) / len(agents) >= quorum else "DISPUTED"
        if ref is None and s != "UNKNOWN":
            s = "UNVERIFIED_" + s              # no deterministic reference: agents only
        counts[s] = counts.get(s, 0) + 1
    return counts
