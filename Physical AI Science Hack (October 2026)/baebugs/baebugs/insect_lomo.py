"""Context in / context out over the TOY print-insect Merkle KG (parametric toys, not replicas): LOMO and LOFO with a
local-model -> Claude -> human cascade, scored by the deterministic insect hash.

Each case holds one insect out (LOMO: leave one model out) or a whole family out
(LOFO). The solver gets
  context IN : the KG records of every other insect (family, plan, length,
               family mean±SD, envelope, top area, appendage counts, tray)
  query      : the held-out insect's OBSERVATION only (envelope at 0.1 mm,
               top-down area, legs/antennae/wings counts) - what the camera sees
and must answer (context OUT) {family, plan, length_mm, novel}.

Two checks, both deterministic:
  escalation (no answer key): rebuild the proposed insect and re-observe it; if
      it does not reproduce the observation, the tier failed -> next tier
      (logic baseline | local Ollama model -> Claude -> human STEP-IN)
  scoring (answer key = the Merkle KG): rebuilt insect hash == held-out insect
      hash (exact), else the break point: plan/topology, tray, length error;
      plus triage (novel expected for every non-California / unseen insect).

  python -m baebugs.insect_lomo --kg print/fuse1/kg --out print/fuse1/kg/lomo \
      --local qwen3:1.7b --claude --ledger
"""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import numpy as np

from .insect_kg import insect_tree, observe
from .printmodels import PLANS, insect_parts

DB_MIN_MM = 2.8
PLAN_LIST = sorted(PLANS)


def _np(o):
    return o.item() if hasattr(o, "item") else str(o)


# --------------------------------------------------------------------- cases

def load_index(kg_dir):
    return json.loads((Path(kg_dir) / "index.json").read_text())


def family_stats(ctx):
    """Context family table: CA families carry the database mean±SD; other
    families only the lengths seen in context."""
    from .printmodels import CA_FAMILIES
    ca = {f: (n, mu, sd) for _, f, n, mu, sd, _ in CA_FAMILIES}
    fams = {}
    for x in ctx:
        f = x["family_base"]
        e = fams.setdefault(f, {"family": f, "order": x["order"], "plans": set(), "lengths": [], "ca": f in ca and x["group"] == "california"})
        e["plans"].add(x["plan"]); e["lengths"].append(x["length_mm"])
        if e["ca"] or (f in ca and x["group"] == "california"):
            e["ca"] = True
    for f, e in fams.items():
        if e["ca"]:
            e["n"], e["mean"], e["sd"] = ca[f]
        e["plans"] = sorted(e["plans"]); e["lengths"] = sorted(e["lengths"])
    return fams


SIZE_BINS = [1.0, 3.0, 6.0, 12.0, 20.0, 30.01]     # mm: XS, S, M, L, XL


def size_bin(L):
    for i in range(len(SIZE_BINS) - 1):
        if SIZE_BINS[i] <= L < SIZE_BINS[i + 1]:
            return f"{SIZE_BINS[i]:g}-{min(SIZE_BINS[i + 1], 30):g}mm"
    return "out"


def cases(index, protocol):
    """Yield (held, context, step). lomo / lofo: step None.
    s2l: small->large curriculum: context = all insects in smaller bins, query = next bin.
    l2s: large->small, the reverse."""
    if protocol == "lomo":
        for i, x in enumerate(index):
            yield x, index[:i] + index[i + 1:], None
    elif protocol == "lofo":
        for x in index:
            yield x, [y for y in index if y["family_base"] != x["family_base"]], None
    elif protocol in ("s2l", "l2s"):
        nb = len(SIZE_BINS) - 1
        order = list(range(nb)) if protocol == "s2l" else list(range(nb))[::-1]
        bins = {k: [x for x in index if SIZE_BINS[k] <= x["length_mm"] < SIZE_BINS[k + 1]] for k in range(nb)}
        for j in range(1, nb):
            ctx = [x for k in order[:j] for x in bins[k]]
            step = f"{j}: train {'+'.join(size_bin(SIZE_BINS[k]) for k in order[:j])} -> test {size_bin(SIZE_BINS[order[j]])}"
            for x in bins[order[j]]:
                yield x, ctx, step
    else:
        raise ValueError(protocol)


def expected_novel(held, ctx):
    """Answer key: not a California database insect, family unseen in context,
    or below the database minimum size."""
    fams = family_stats(ctx)
    return held["group"] != "california" or held["family_base"] not in fams or held["length_mm"] < DB_MIN_MM


def novelty_logic(family, length_mm, fams):
    """Deterministic triage of a reconstructed insect against the context."""
    if length_mm is None:
        return True, "no length"
    if length_mm < DB_MIN_MM:
        return True, f"below database minimum {DB_MIN_MM} mm"
    f = fams.get(family)
    if f is None:
        return True, "family not in context"
    if f.get("mean") is not None:
        z = (length_mm - f["mean"]) / f["sd"]
        return (abs(z) > 2.05, f"z={z:+.2f}")
    return True, "family outside the CA database (seen only as novel)"


# --------------------------------------------------------------- verification

_obs_cache = {}


def rebuild_observation(length_mm, plan):
    key = (round(float(length_mm), 2), plan)
    if key not in _obs_cache:
        _nodes, root = insect_tree(*key)
        _obs_cache[key] = (observe(root), root["hash"], root["topo"], root["kit_tray"])
    return _obs_cache[key]


def obs_consistent(a, b, env_tol=0.15, area_rel=0.03):
    return (all(abs(x - y) <= env_tol for x, y in zip(a["envelope_mm"], b["envelope_mm"]))
            and abs(a["top_area_mm2"] - b["top_area_mm2"]) <= max(2.0, area_rel * b["top_area_mm2"])
            and all(a[k] == b[k] for k in ("legs", "antennae", "wings")))


def check(answer, held, ctx):
    """Escalation check (observation only) + scoring (insect hash)."""
    fams = family_stats(ctx)
    out = {"answer": answer, "valid": False, "obs_consistent": False, "hash_match": False}
    try:
        plan = answer["plan"]; L = round(float(answer["length_mm"]), 1)
        assert plan in PLANS and 0.5 <= L <= 40
    except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
        out["break_point"] = "invalid answer"
        out["triage_ok"] = False
        return out
    obs, h, topo, tray = rebuild_observation(L, plan)
    out.update(valid=True, obs_consistent=obs_consistent(obs, held["observation"]),
               hash_match=h == held["insect_hash"], topo_match=topo == held["topo_hash"],
               tray_match=tray == held["kit_tray"], length_err_mm=round(L - held["length_mm"], 2),
               family_match=answer.get("family") == held["family_base"])
    nov, why = novelty_logic(answer.get("family"), L, fams)
    exp = expected_novel(held, ctx)
    out.update(novel_logic=nov, novel_why=why, novel_model=bool(answer.get("novel")), expected_novel=exp,
               triage_ok=nov == exp)
    out["break_point"] = ("none (exact insect hash)" if out["hash_match"] else
                          "L3 topology (plan / appendages)" if not out["topo_match"] else
                          "L3 kit tray (width)" if not out["tray_match"] else
                          f"L0 primitives (length off {out['length_err_mm']:+.1f} mm)")
    return out


# ------------------------------------------------------------------- solvers

def _env_fast(L, plan):
    prims, _, _ = insect_parts(L, plan)
    lo = np.min([m.bounds[0] for p in prims for m in p["meshes"]], axis=0)
    hi = np.max([m.bounds[1] for p in prims for m in p["meshes"]], axis=0)
    # same rounding path as insect_kg.observe: bbox -> 0.01 mm, extent -> 0.01, then 0.1
    lo, hi = np.array(_r2(lo)), np.array(_r2(hi))
    ext = [round(round(float(h - l), 2), 1) for l, h in zip(lo, hi)]
    c = {"legs": 0, "antennae": 0, "wings": 0}
    for p in prims:
        if p["seg"] == "femur": c["legs"] += 1
        if p["seg"] == "antenna": c["antennae"] += 1
        if p["kind"] == "plate": c["wings"] += 1
    return ext, c


def _r2(a):
    return [0.0 if round(float(v), 2) == 0 else round(float(v), 2) for v in a]


_twin = None


def twin_table(step=0.1, lo=0.5, hi=35.0):
    """Digital twin lookup: envelope + counts for every plan x length (0.1 mm)."""
    global _twin
    if _twin is None:
        _twin = [(plan, round(float(L), 1), *_env_fast(float(L), plan)) for plan in PLAN_LIST
                 for L in np.arange(lo, hi + 1e-9, step)]
    return _twin


def solve_logic(held_obs, ctx):
    """Analysis by synthesis: search the twin for (plan, length) reproducing the
    envelope and appendage counts, then name the family from context."""
    best = None
    for plan, L, env, c in twin_table():
        if any(c[k] != held_obs[k] for k in c):
            continue
        err = sum(abs(a - b) for a, b in zip(env, held_obs["envelope_mm"]))
        if best is None or err < best[0]:
            best = (err, plan, L)
    if best is None:
        return {"plan": None, "length_mm": None, "family": None, "novel": True, "reason": "no twin match"}
    _, plan, L = best
    tied_plans = sorted({p for p, l, env, c in twin_table()
                         if all(c[k] == held_obs[k] for k in c)
                         and sum(abs(a - b) for a, b in zip(env, held_obs["envelope_mm"])) <= best[0] + 1e-9})
    # refine with area among near-ties
    ties = [(p, l) for p, l, env, c in twin_table() if p == plan and abs(l - L) <= 0.3
            and all(c[k] == held_obs[k] for k in c)]
    if len(ties) > 1:
        L = min(ties, key=lambda t: abs(rebuild_observation(t[1], t[0])[0]["top_area_mm2"] - held_obs["top_area_mm2"])
                + 10 * sum(abs(a - b) for a, b in zip(rebuild_observation(t[1], t[0])[0]["envelope_mm"], held_obs["envelope_mm"])))[1]
    fams = family_stats(ctx)
    cands = [f for f in fams.values() if plan in f["plans"]]

    def score(f):                      # database (CA) families first, then novel-only families
        if f.get("mean") is not None:
            return abs(L - f["mean"]) / f["sd"]
        return 2.05 + min(abs(L - l) for l in f["lengths"]) / 2.0
    fam = min(cands, key=score)["family"] if cands else None
    nov, why = novelty_logic(fam, L, fams)
    return {"plan": plan, "length_mm": L, "family": fam, "novel": nov, "reason": f"twin search; {why}",
            "tied_plans": tied_plans, "ambiguous": len(tied_plans) > 1}


SYSTEM = """You reconstruct 3D-printed insect size standards from what a camera sees.
Body plans: {plans}.
Rules: legs (6) only when length >= 6 mm and the plan has legs; antennae (2) when length >= 12 mm (not damselfly);
wings (2) when length >= 8 mm and the plan has wings. Envelope = x (body axis, includes antennae) , y, z in mm.
NOVEL = family not in the context, OR length outside family mean +/- 2 SD, OR length < 2.8 mm (below the database).
Answer ONLY JSON: {{"family": str, "plan": one of the body plans, "length_mm": number with one decimal, "novel": bool, "reason": short}}"""


def context_text(ctx):
    fams = family_stats(ctx)
    lines = ["FAMILIES (family | order | plans | database mean±SD n | lengths in context):"]
    for f in sorted(fams.values(), key=lambda e: e["family"]):
        st = f"{f['mean']}±{f['sd']} n={f['n']}" if f.get("mean") is not None else "no CA stats"
        lines.append(f"{f['family']} | {f['order']} | {','.join(f['plans'])} | {st} | {f['lengths']}")
    lines.append("\nINSECTS (family | plan | length_mm | envelope x,y,z | top_area mm2 | legs,antennae,wings | tray):")
    for x in sorted(ctx, key=lambda e: (e["plan"], e["length_mm"])):
        o = x["observation"]
        lines.append(f"{x['family_base']} | {x['plan']} | {x['length_mm']} | {o['envelope_mm']} | {o['top_area_mm2']:.0f} | "
                     f"{o['legs']},{o['antennae']},{o['wings']} | {x['kit_tray']}")
    return "\n".join(lines)


def query_text(obs, qid=None):
    q = (f"envelope x,y,z = {obs['envelope_mm']} mm; top area = {obs['top_area_mm2']:.0f} mm2; "
         f"legs,antennae,wings = {obs['legs']},{obs['antennae']},{obs['wings']}")
    return f"[{qid}] {q}" if qid is not None else q


def _parse_json(text):
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1)
    for o, c in (("[", "]"), ("{", "}")):
        i, j = text.find(o), text.rfind(c)
        if i >= 0 and j > i:
            try:
                return json.loads(text[i:j + 1])
            except Exception:  # noqa: BLE001,S110 - best-effort, nothing to record
                pass
    return None


def ask_ollama(model, ctx_txt, obs, host="http://localhost:11434", timeout=180):
    body = {"model": model, "stream": False, "format": "json",
            "options": {"temperature": 0, "num_ctx": 12288, "seed": 0, "num_predict": 1024},
            "messages": [{"role": "system", "content": SYSTEM.format(plans=", ".join(PLAN_LIST))},
                         {"role": "user", "content": ctx_txt + "\n\nHELD-OUT INSECT: " + query_text(obs)}]}
    if model.startswith("qwen3"):
        body["think"] = False
    req = urllib.request.Request(f"{host}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
        txt = r["message"]["content"]
    except Exception as e:  # noqa: BLE001 - timeouts, HTTP errors
        return None, f"error {e}", time.time() - t
    return _parse_json(txt), txt[:400], time.time() - t


def ask_claude_batch(ctx_txt, items, model=None, timeout=900):
    """One `claude -p` call: shared context, several held-out queries (same
    context only). items = [(qid, obs)]. Returns {qid: answer}."""
    prompt = (SYSTEM.format(plans=", ".join(PLAN_LIST)).replace("Answer ONLY JSON: {", "Answer ONLY a JSON list, one object per query with \"id\" plus: {")
              + "\n\n" + ctx_txt + "\n\nHELD-OUT INSECTS:\n" + "\n".join(query_text(o, q) for q, o in items))
    cmd = ["claude", "-p", "--output-format", "json", "--max-turns", "1"]
    if model:
        cmd += ["--model", model]
    t = time.time()
    with tempfile.TemporaryDirectory() as d:
        try:
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=d, check=False)
            res = json.loads(p.stdout).get("result", "")
        except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
            return {}, f"error {e}", time.time() - t
    arr = _parse_json(res)
    out = {}
    if isinstance(arr, dict):
        arr = [arr]
    for a in arr or []:
        if isinstance(a, dict) and "id" in a:
            out[str(a["id"])] = a
    return out, res[:400], time.time() - t


# ------------------------------------------------------------------- running

def run(kg_dir, out_dir, protocols=("lomo", "lofo"), local=None, use_claude=False, claude_model=None,
        claude_batch=12, claude_max_calls=40, ledger=None, limit=None):
    index = load_index(kg_dir)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    summary = {}
    twin_table()
    for proto in protocols:
        rows = []
        for i, (held, ctx, step) in enumerate(cases(index, proto)):
            if limit and i >= limit:
                break
            r = {"protocol": proto, "step": step, "training_role": held.get("training_role", ""),
                 "size_bin": size_bin(held["length_mm"]), "held": held["name"], "group": held["group"], "family": held["family_base"],
                 "plan": held["plan"], "length_mm": held["length_mm"], "insect_hash": held["insect_hash"][:16]}
            r["logic"] = check(solve_logic(held["observation"], ctx), held, ctx)
            if local:
                ans, raw, dt = ask_ollama(local, context_text(ctx), held["observation"])
                r["local"] = {**check(ans or {}, held, ctx), "model": local, "seconds": round(dt, 1), "raw": raw}
                if i % 10 == 0:
                    print(f"[{proto}] {local} {i} {dt:.1f}s hash={r['local']['hash_match']}", flush=True)
            rows.append((r, held, ctx))
        # Claude on local misses (escalation by observation check only), batched by shared context
        if use_claude:
            esc = [(r, h, c) for r, h, c in rows if not (local and r["local"]["obs_consistent"])]
            groups = {}
            for r, h, c in esc:
                key = tuple(sorted(x["name"] for x in c))
                groups.setdefault(key, []).append((r, h, c))
            calls = 0
            for key, items in groups.items():
                for k in range(0, len(items), claude_batch):
                    if calls >= claude_max_calls:
                        break
                    chunk = items[k:k + claude_batch]
                    ans, raw, dt = ask_claude_batch(context_text(chunk[0][2]),
                                                    [(str(j), h["observation"]) for j, (_, h, _) in enumerate(chunk)],
                                                    model=claude_model)
                    calls += 1
                    for j, (r, h, c) in enumerate(chunk):
                        r["claude"] = {**check(ans.get(str(j), {}), h, c), "seconds_batch": round(dt, 1),
                                       "batch_size": len(chunk)}
        # cascade outcome
        for r, h, c in rows:
            tiers = [t for t in ("local", "claude") if t in r]
            res = next((t for t in tiers if r[t]["obs_consistent"]), None)
            r["cascade"] = {"resolved_by": res or "STEP-IN (human)",
                            "hash_match": bool(res and r[res]["hash_match"]),
                            "triage_ok": bool(res and r[res]["triage_ok"])}
        recs = [r for r, _, _ in rows]
        steps = sorted({r["step"] for r in recs if r.get("step")})
        with (out / f"{proto}.jsonl").open("w") as f:
            for r in recs:
                f.write(json.dumps(r, default=_np) + "\n")
        summary[proto] = summarize(recs)
        if steps:
            summary[proto]["steps"] = {st: summarize([r for r in recs if r.get("step") == st]) for st in steps}
        if ledger is not None:
            ledger.append(f"{proto}_done", json.loads(json.dumps(summary[proto], default=_np)), files={proto: out / f"{proto}.jsonl"})
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=_np))
    write_csv(out, summary)
    return summary


def summarize(recs):
    s = {"cases": len(recs)}
    for t in ("logic", "local", "claude"):
        rs = [r[t] for r in recs if t in r]
        if not rs:
            continue
        s[t] = {"n": len(rs),
                "valid": sum(x["valid"] for x in rs),
                "obs_consistent": sum(x["obs_consistent"] for x in rs),
                "exact_hash": sum(x["hash_match"] for x in rs),
                "topology_ok": sum(bool(x.get("topo_match")) for x in rs),
                "tray_ok": sum(bool(x.get("tray_match")) for x in rs),
                "family_ok": sum(bool(x.get("family_match")) for x in rs),
                "triage_ok": sum(bool(x.get("triage_ok")) for x in rs),
                "median_abs_len_err_mm": float(np.median([abs(x["length_err_mm"]) for x in rs if "length_err_mm" in x])) if any("length_err_mm" in x for x in rs) else None}
        neg = [r[t] for r in recs if t in r and r.get("training_role", "").startswith("edge_negative")]
        s[t]["edge_negatives"] = len(neg)
        s[t]["edge_negatives_rejected"] = sum(bool(x.get("novel_logic")) for x in neg)
    if any("cascade" in r for r in recs):
        by = {}
        for r in recs:
            by[r["cascade"]["resolved_by"]] = by.get(r["cascade"]["resolved_by"], 0) + 1
        s["cascade"] = {"resolved_by": by, "exact_hash": sum(r["cascade"]["hash_match"] for r in recs),
                        "triage_ok": sum(r["cascade"]["triage_ok"] for r in recs)}
    return s


def write_csv(out, summary):
    import csv
    with (Path(out) / "summary.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["protocol", "step", "tier", "n", "valid", "obs_consistent", "exact_hash", "topology_ok", "tray_ok",
                    "family_ok", "triage_ok", "edge_negatives", "edge_negatives_rejected", "median_abs_len_err_mm"])
        for p, s in summary.items():
            blocks = [("all", s)] + list(s.get("steps", {}).items())
            for st, b in blocks:
                for t in ("logic", "local", "claude"):
                    if t in b:
                        x = b[t]
                        w.writerow([p, st, t, x["n"], x["valid"], x["obs_consistent"], x["exact_hash"], x["topology_ok"],
                                    x["tray_ok"], x["family_ok"], x["triage_ok"], x["edge_negatives"],
                                    x["edge_negatives_rejected"], x["median_abs_len_err_mm"]])


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-insect-lomo")
    ap.add_argument("--kg", default="print/fuse1/kg")
    ap.add_argument("--out", default="print/fuse1/kg/lomo")
    ap.add_argument("--protocols", default="lomo,lofo,s2l,l2s")
    ap.add_argument("--local", help="Ollama model, e.g. qwen3:1.7b")
    ap.add_argument("--claude", action="store_true", help="escalate local misses to `claude -p`")
    ap.add_argument("--claude-model")
    ap.add_argument("--claude-max-calls", type=int, default=40)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ledger", action="store_true")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    led = None
    if a.ledger:
        from .git_ledger import GitLedger
        led = GitLedger("print_kg_lomo", a.repo)
    s = run(a.kg, a.out, a.protocols.split(","), a.local, a.claude, a.claude_model,
            claude_max_calls=a.claude_max_calls, ledger=led, limit=a.limit)
    print(json.dumps(s, indent=1, default=_np))


if __name__ == "__main__":
    main()
