"""Multi-verifier attestation with Merkle chain of custody.

A CLAIM is content-addressed: its id hashes the subject (input hashes), the
logic (statement + code reference + version), the VARIANCE POLICY (tolerances that
count as agreement; never part of value identity) and the CONSENSUS RULE.
Change any of them and the claim id changes, visibly.

ACTORS are verifiers with content-addressed identities (FCO style): deterministic
code (repo + commit + function), a model (provider/slug/version or weights hash),
an agent, a human (public-key hash). Names are labels only; the id is the hash.

An ATTESTATION is a leaf: claim id + actor id + observed value(s) + verdict +
residual against the claim + whether it is within policy + evidence hashes.
The claim's attestation root covers all leaves; the STATUS is recomputed from
leaves + policy by anyone:
  SUPPORTED   deterministic verifier(s) pass and the agent quorum agrees within policy
  DISPUTED    verifiers disagree beyond policy -> VIP / human step-in
  FAILED      deterministic verifier fails
  UNKNOWN     not enough attestations yet
Context quadrant (self / non-self x within / outside policy) is reported per leaf:
self = code from this repository, non-self = any external model or person.

An attestation about an attestation is a claim whose subject is that leaf:
information about information, chained.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from .explore import merkle_root

SCHEMA = "baebugs.attest.v1"


def H(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


# ------------------------------------------------------------------ actors

def actor(kind, name, version=None, key=None, **meta):
    """kind: code | model | agent | human. key: public key / weights hash / commit."""
    body = {"schema": SCHEMA, "type": "actor", "kind": kind, "name": name, "version": version, "key": key, **meta}
    return {**body, "id": H(body)}


def code_actor(func, commit):
    return actor("code", f"{func.__module__}.{func.__qualname__}", version=commit, key=commit,
                 self_or_nonself="self")


# ------------------------------------------------------------------ claims

def claim(subject, statement, logic_ref, expected=None, policy=None, consensus=None):
    """subject: dict of input hashes (what the claim is about).
    expected: value(s) the claim asserts (numbers, strings, bools, dict of these).
    policy:   {"abs": 1e-9, "rel": 0.0} per value or globally; exact match for non-numbers.
    consensus:{"deterministic_required": True, "min_agents": 0, "quorum": 0.5}."""
    policy = policy or {"abs": 0.0, "rel": 0.0}
    consensus = consensus or {"deterministic_required": True, "min_agents": 0, "quorum": 0.5}
    body = {"schema": SCHEMA, "type": "claim", "subject": subject, "statement": statement,
            "logic": logic_ref, "expected": expected, "policy": policy, "consensus": consensus}
    return {**body, "id": H(body)}


def _within(exp, obs, pol):
    if isinstance(exp, dict):
        if not isinstance(obs, dict) or set(exp) - set(obs):
            return False, {"missing": sorted(set(exp) - set(obs or {}))}
        res = {k: _within(exp[k], obs[k], pol.get(k, pol) if isinstance(pol.get(k), dict) else pol) for k in exp}
        return all(r[0] for r in res.values()), {k: r[1] for k, r in res.items()}
    if isinstance(exp, bool) or not isinstance(exp, (int, float)) or not isinstance(obs, (int, float)):
        return exp == obs, (None if exp == obs else {"expected": exp, "observed": obs})
    d = abs(float(obs) - float(exp))
    tol = max(float(pol.get("abs", 0.0)), float(pol.get("rel", 0.0)) * abs(float(exp)))
    return (d <= tol or (math.isnan(d) is False and d == 0)), round(d, 12)


def attest(c, who, observed, evidence=None, note=None, t=None):
    """One verifier's attestation of a claim (a leaf)."""
    ok, residual = _within(c["expected"], observed, c["policy"]) if c["expected"] is not None else (bool(observed), None)
    body = {"schema": SCHEMA, "type": "attestation", "claim": c["id"], "actor": who["id"], "actor_kind": who["kind"],
            "observed": observed, "residual": residual, "within_policy": bool(ok), "evidence": evidence or {},
            "note": note, "t": t if t is not None else round(time.time(), 3),
            "quadrant": f"{'self' if who.get('self_or_nonself') == 'self' else 'non-self'}/"
                        f"{'within' if ok else 'outside'}"}
    return {**body, "leaf": H(body)}


def status(c, leaves):
    """Deterministic verdict from leaves + the claim's consensus rule."""
    rule = c["consensus"]
    det = [l for l in leaves if l["actor_kind"] == "code"]
    agents = [l for l in leaves if l["actor_kind"] != "code"]
    if rule.get("deterministic_required", True):
        if not det:
            return "UNKNOWN"
        if not all(l["within_policy"] for l in det):
            return "FAILED"
    if len(agents) < rule.get("min_agents", 0):
        return "UNKNOWN"
    if agents:
        agree = sum(l["within_policy"] for l in agents) / len(agents)
        if agree < rule.get("quorum", 0.5):
            return "DISPUTED"
    return "SUPPORTED"


def claim_root(c, leaves):
    mine = [l for l in leaves if l["claim"] == c["id"]]
    return {"claim": c["id"], "n": len(mine), "root": merkle_root(sorted(l["leaf"] for l in mine)) if mine else None,
            "status": status(c, mine)}


def verify_leaf(l):
    body = {k: v for k, v in l.items() if k != "leaf"}
    return H(body) == l["leaf"]


def verify_claim(c):
    body = {k: v for k, v in c.items() if k != "id"}
    return H(body) == c["id"]


# ------------------------------------------------------------------ ledger

class AttestationLedger:
    """Append-only jsonl of actors, claims and attestations; roots on demand."""

    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, rec):
        with self.path.open("a") as f:
            f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec

    def load(self):
        recs = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()] if self.path.exists() else []
        return ({r["id"]: r for r in recs if r.get("type") == "actor"},
                {r["id"]: r for r in recs if r.get("type") == "claim"},
                [r for r in recs if r.get("type") == "attestation"])

    def roots(self):
        actors, claims, leaves = self.load()
        bad = [l["leaf"] for l in leaves if not verify_leaf(l)] + [c for c, v in claims.items() if not verify_claim(v)]
        per = {cid: claim_root(c, leaves) for cid, c in claims.items()}
        counts = {}
        for r in per.values():
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        return {"tampered": bad, "claims": len(claims), "attestations": len(leaves), "actors": len(actors),
                "status_counts": counts,
                "root": merkle_root(sorted(r["root"] for r in per.values() if r["root"])) if per else None,
                "per_claim": per}
