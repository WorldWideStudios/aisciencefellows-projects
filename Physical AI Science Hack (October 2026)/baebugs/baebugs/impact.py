"""Frozen source of truth + MMR of evaluations: the impact of weights and values.

TRUTH (frozen, never edited; a new truth is a new file + id):
  sources  toy KG collection root, toy index sha256, DAISY datasets root,
           DAISY protocol sha256, code commit
  claims   one per toy: "the held-out toy reconstructs to (plan, length)";
           expected = frozen KG values. Claim ids hash subject + logic; the
           variance policy is a VALUE applied per event, so the same truth can be
           evaluated under different tolerances and the effect is visible.
MMR (append-only, every event provable later):
  leaf 0   the truth itself
  events   one per (actor weights x values): actor id (code commit / model slug +
           digest / weights sha256), values (policy + consensus), attestation root,
           pass/fail per claim, and IMPACT:
             vs_truth     claims not reproduced
             vs_baseline  flips against the deterministic code actor at the same values
             vs_previous  flips against the same actor's previous event (new weights)
             vs_values    flips against the same actor under the default values
  consensus events: per values, code + all agents -> SUPPORTED / DISPUTED / FAILED

  python -m baebugs.impact freeze                 # writes daisy/TRUTH-001.json (refuses to overwrite)
  python -m baebugs.impact replay                 # appends events for every result file present
  python -m baebugs.impact append --actor-name X --kind model --weights W --results file.jsonl --tier local
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path

from . import attest as A
from .mmr import MMRLog

TRUTH = Path("daisy/TRUTH-001.json")
LOG = Path("daisy/impact_mmr.jsonl")
KG = Path("print/fuse1/kg")

VALUES = {   # variance policies (values) evaluated against the same truth
    "exact":      {"policy": {"abs": 0.0, "length_mm": {"abs": 0.05}}, "fields": ["plan", "length_mm"]},
    "tol_0.5mm":  {"policy": {"abs": 0.0, "length_mm": {"abs": 0.5}}, "fields": ["plan", "length_mm"]},
    "tol_2mm":    {"policy": {"abs": 0.0, "length_mm": {"abs": 2.0}}, "fields": ["plan", "length_mm"]},
    "plan_only":  {"policy": {"abs": 0.0}, "fields": ["plan"]},
}
CONSENSUS = {"deterministic_required": True, "min_agents": 1, "quorum": 0.5}


def _sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _commit():
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip() or None


def freeze(truth_path=TRUTH, kg=KG):
    truth_path = Path(truth_path)
    if truth_path.exists():
        raise SystemExit(f"{truth_path} is frozen; make TRUTH-002 instead of editing it")
    idx = json.loads((Path(kg) / "index.json").read_text())
    coll = json.loads((Path(kg) / "collection.json").read_text())
    subjects = [{"toy": x["name"], "insect_hash": x["insect_hash"], "plan": x["plan"], "length_mm": x["length_mm"],
                 "training_role": x.get("training_role"), "representation": x.get("representation", "toy")} for x in idx]
    t = {"schema": "baebugs.truth.v1", "id": None, "name": "TRUTH-001",
         "statement": "held-out toy reconstructs to its frozen (plan, length)",
         "sources": {"toy_kg_collection_root": coll["root"]["hash"], "toy_index_sha256": _sha_file(Path(kg) / "index.json"),
                     "daisy_datasets_root": json.loads(Path("daisy/datasets.json").read_text())["root"]
                     if Path("daisy/datasets.json").exists() else None,
                     "daisy_protocol_sha256": _sha_file("daisy/DAISY-BB-001.json") if Path("daisy/DAISY-BB-001.json").exists() else None,
                     "code_commit": _commit()},
         "subjects": subjects}
    t["subjects_root"] = A.merkle_root(sorted(A.H(s) for s in subjects))
    t["id"] = A.H({k: v for k, v in t.items() if k != "id"})
    truth_path.write_text(json.dumps(t, indent=1))
    log = MMRLog(LOG)
    if not log.records:
        log.append({"type": "truth", "truth_id": t["id"], "name": t["name"], "sources": t["sources"],
                    "subjects_root": t["subjects_root"], "n_subjects": len(subjects)})
    return t


def load_truth():
    t = json.loads(TRUTH.read_text())
    body = {k: v for k, v in t.items() if k != "id"}
    if A.H(body) != t["id"]:
        raise SystemExit("TRUTH-001 does not match its id: the source of truth was edited")
    return t


def claims_for(truth, values_name):
    v = VALUES[values_name]
    out = {}
    for s in truth["subjects"]:
        exp = {f: s[f] for f in v["fields"]}
        out[s["toy"]] = A.claim({"truth": truth["id"], "toy": s["toy"], "insect_hash": s["insect_hash"]},
                                truth["statement"], "baebugs.insect_lomo.check", exp, v["policy"], CONSENSUS)
    return out


def observations(results_path, tier):
    """{toy: {"plan", "length_mm"} | None} from a LOMO results jsonl (insect_lomo / model_compare)."""
    obs = {}
    for line in Path(results_path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("protocol", "lomo") != "lomo":
            continue
        a = (r.get(tier) or {}).get("answer") or {}
        try:
            obs[r["held"]] = {"plan": a.get("plan"), "length_mm": round(float(a["length_mm"]), 2)}
        except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
            obs[r["held"]] = None
    return obs


def event(truth, who, weights, values_name, obs, log, extra=None):
    claims = claims_for(truth, values_name)
    fields = VALUES[values_name]["fields"]
    leaves, passed = [], {}
    for toy, c in claims.items():
        o = obs.get(toy)
        o = {f: (o or {}).get(f) for f in fields} if o else {f: None for f in fields}
        l = A.attest(c, who, o, t=0)        # t=0: replays are byte-reproducible
        leaves.append(l); passed[toy] = l["within_policy"]
    prev = [r["record"] for r in log.records if r["record"].get("type") == "evaluation"]
    def flips(other):
        if not other:
            return None
        op = other["passed"]
        return {"gained": sorted(k for k in passed if passed[k] and not op.get(k)),
                "lost": sorted(k for k in passed if op.get(k) and not passed[k])}
    base = next((r for r in prev if r["actor"]["kind"] == "code" and r["values"] == values_name
                 and r["actor"]["name"] == "logic-twin"), None)
    same_actor = [r for r in prev if r["actor"]["name"] == who["name"] and r["values"] == values_name]
    same_weights_default = next((r for r in prev if r["actor"]["id"] == who["id"] and r["values"] == "exact"), None)
    rec = {"type": "evaluation", "truth_id": truth["id"], "actor": {"id": who["id"], "name": who["name"], "kind": who["kind"]},
           "weights": weights, "values": values_name, "values_hash": A.H(VALUES[values_name]),
           "consensus": CONSENSUS, "n": len(leaves), "pass": sum(passed.values()),
           "attestation_root": A.merkle_root(sorted(l["leaf"] for l in leaves)), "passed": passed,
           "impact": {"vs_truth": len(leaves) - sum(passed.values()),
                      "vs_baseline": flips(base), "vs_previous": flips(same_actor[-1] if same_actor else None),
                      "vs_values": flips(same_weights_default) if values_name != "exact" else None},
           **(extra or {})}
    log.append(rec)
    return rec, leaves


def consensus_event(truth, values_name, per_actor_leaves, log):
    claims = claims_for(truth, values_name)
    counts, by = {}, {}
    for toy, c in claims.items():
        ls = [l for leaves in per_actor_leaves for l in leaves if l["claim"] == c["id"]]
        s = A.status(c, ls); by[toy] = s; counts[s] = counts.get(s, 0) + 1
    rec = {"type": "consensus", "truth_id": truth["id"], "values": values_name,
           "actors": sorted({l["actor"] for leaves in per_actor_leaves for l in leaves}),
           "status_counts": counts, "status": by,
           "disputed": sorted(k for k, v in by.items() if v == "DISPUTED")}
    log.append(rec)
    return rec


def available_results():
    """(actor, weights, results file, tier) for every evaluation present in the repo."""
    out = [(A.actor("code", "logic-twin", _commit(), key="baebugs.insect_lomo.solve_logic", self_or_nonself="self"),
            {"code": "baebugs.insect_lomo.solve_logic"}, KG / "lomo" / "lomo.jsonl", "logic")]
    digests = {"qwen3_1.7b": "8f68893c685c", "lfm2.5-1.2b-instruct_q4_k_m": "23a7c8003757", "qwen2.5_1.5b": "65ec06548149",
               "lfm2.5-1.2b-thinking_q4_k_m": "fb0859e74b54"}
    for d in sorted((KG / "compare" / "text").glob("*/lomo.jsonl")):
        name = d.parent.name
        out.append((A.actor("model", name, digests.get(name), key=f"ollama:{digests.get(name)}"),
                    {"ollama_digest": digests.get(name)}, d, "local"))
    return out


def vision_results():
    out = []
    weights = {"yolo": "r3_real/weights/best.pt", "yoloe": "yoloe-11s-seg.pt", "classical": "otsu (code)"}
    for f in sorted((KG / "compare" / "vision").glob("*.jsonl")):
        method, ppm = f.stem.rsplit("_ppm", 1)
        # measurers are attesting agents, never the reference verifier (only the logic twin is)
        out.append((A.actor("measurer", f"{method}@{ppm}px/mm", weights.get(method),
                            key=weights.get(method), self_or_nonself="self" if method == "classical" else "non-self"),
                    {"weights": weights.get(method), "ppm": float(ppm)}, f))
    return out


def vision_obs(f):
    obs = {}
    for line in Path(f).read_text().splitlines():
        r = json.loads(line); a = (r.get("tier") or {}).get("answer") or {}
        try:
            obs[r["held"]] = {"plan": a.get("plan"), "length_mm": round(float(a["length_mm"]), 2)}
        except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
            obs[r["held"]] = None
    return obs


def replay(values=tuple(VALUES)):
    truth = load_truth()
    log = MMRLog(LOG)
    done = {(r["record"]["actor"]["id"], r["record"]["values"], r["record"].get("attestation_root"))
            for r in log.records if r["record"].get("type") == "evaluation"}
    new = 0
    for vn in values:
        per = []
        for who, w, path, tier in available_results():
            if not Path(path).exists():
                continue
            rec, leaves = _maybe(truth, who, w, vn, observations(path, tier), log, done)
            new += rec is not None; per.append(leaves)
        for who, w, path in vision_results():
            rec, leaves = _maybe(truth, who, w, vn, vision_obs(path), log, done, extra={"input": "image"})
            new += rec is not None; per.append(leaves)
        if new:
            consensus_event(truth, vn, per, log)
    write_csv(log)
    return log, new


def _maybe(truth, who, w, vn, obs, log, done, extra=None):
    # skip identical re-evaluations (same actor, values, attestation root)
    claims = claims_for(truth, vn); fields = VALUES[vn]["fields"]
    leaves = [A.attest(c, who, {f: (obs.get(t) or {}).get(f) for f in fields} if obs.get(t) else {f: None for f in fields}, t=0)
              for t, c in claims.items()]
    root = A.merkle_root(sorted(l["leaf"] for l in leaves))
    if (who["id"], vn, root) in done:
        return None, leaves
    rec, leaves = event(truth, who, w, vn, obs, log, extra)
    return rec, leaves


def write_csv(log, path="daisy/impact_events.csv"):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "type", "actor", "kind", "weights", "values", "n", "pass", "not_reproduced",
                    "gained_vs_baseline", "lost_vs_baseline", "gained_vs_values", "lost_vs_values", "status_counts", "mmr_root"])
        for r in log.records:
            x = r["record"]
            if x["type"] == "evaluation":
                i = x["impact"]
                b, v = i.get("vs_baseline") or {}, i.get("vs_values") or {}
                w.writerow([r["index"], "evaluation", x["actor"]["name"], x["actor"]["kind"], json.dumps(x["weights"]),
                            x["values"], x["n"], x["pass"], i.get("vs_truth", x["n"] - x["pass"]), len(b.get("gained", [])), len(b.get("lost", [])),
                            len(v.get("gained", [])), len(v.get("lost", [])), "", r["root"][:16]])
            elif x["type"] == "consensus":
                w.writerow([r["index"], "consensus", "+".join(a[:6] for a in x["actors"]), "", "", x["values"], "", "", "",
                            "", "", "", "", json.dumps(x["status_counts"]), r["root"][:16]])
            else:
                w.writerow([r["index"], x["type"], "", "", "", "", x.get("n_subjects"), "", "", "", "", "", "", "", r["root"][:16]])


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-impact")
    ap.add_argument("cmd", choices=["freeze", "replay", "verify", "append"])
    ap.add_argument("--actor-name"); ap.add_argument("--kind", default="model")
    ap.add_argument("--weights"); ap.add_argument("--results"); ap.add_argument("--tier", default="local")
    ap.add_argument("--values", default=",".join(VALUES))
    ap.add_argument("--ledger", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "freeze":
        t = freeze(); print("TRUTH", t["id"][:16], len(t["subjects"]), "subjects")
    elif a.cmd == "verify":
        load_truth(); print(MMRLog(LOG).verify())
    elif a.cmd == "replay":
        log, new = replay(tuple(a.values.split(",")))
        print(f"{new} new events; MMR size {len(log.records)} root {log.mmr.root[:16]}")
    elif a.cmd == "append":
        truth, log = load_truth(), MMRLog(LOG)
        who = A.actor(a.kind, a.actor_name, a.weights, key=a.weights)
        for vn in a.values.split(","):
            rec, _ = event(truth, who, {"weights": a.weights}, vn, observations(a.results, a.tier), log)
            print(vn, rec["pass"], "/", rec["n"], rec["impact"]["vs_baseline"] and {k: len(v) for k, v in rec["impact"]["vs_baseline"].items()})
        write_csv(log)
    if a.ledger and a.cmd in ("freeze", "replay", "append"):
        from .git_ledger import GitLedger
        log = MMRLog(LOG)
        GitLedger("impact_mmr", ".").append(f"impact_{a.cmd}", {"mmr_size": len(log.records), "mmr_root": log.mmr.root},
                                            files={"mmr": LOG, "truth": TRUTH})


if __name__ == "__main__":
    main()
