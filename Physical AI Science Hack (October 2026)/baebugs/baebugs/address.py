"""Addresses above the weights: information -> recipe -> realization -> behaviour.

Training without determinism produces different weight bytes from the same
inputs, so a weight hash identifies a REALIZATION, not knowledge. Identity lives
higher in the graph:

  L0 information  frozen sources: TRUTH id, dataset Merkle roots, toy KG root
  L1 recipe       what was asked for: protocol id + the run's train/val members (by
                  their L0 roots) + settings that define the method; run-to-run noise
                  (seed when non-deterministic, AMP decision, environment) is excluded
  L2 realization  weights sha256 + environment + gate evidence root (expected to differ)
  L3 behaviour    the claims a realization satisfies under a variance policy;
                  realizations of one recipe are EQUIVALENT if their behaviour agrees
                  within policy, otherwise the recipe has a break point

Each address is a hash of its parent address plus its own content, so the graph
can be walked from any weight file up to the frozen information it came from.
"""
from __future__ import annotations

import hashlib
import json

NOISE_SETTINGS = {"amp", "workers", "seed_if_nondeterministic"}


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def information(truth_id, dataset_roots: dict, extra=None):
    body = {"level": "L0_information", "truth": truth_id, "datasets": dict(sorted(dataset_roots.items())), **(extra or {})}
    return {**body, "address": H(body)}


def recipe(info_addr, protocol: dict, run: dict):
    s = {k: v for k, v in protocol.get("settings", {}).items() if k not in NOISE_SETTINGS}
    if not s.get("deterministic", True):
        s.pop("seed", None)                     # with determinism off the seed does not pin the outcome
    roots = protocol.get("roots", {})
    body = {"level": "L1_recipe", "parent": info_addr, "protocol_family": protocol["id"].rstrip("abcdefgh"),
            "run": run["name"], "train": {m: roots.get(m) for m in run["train"]},
            "val": {m: roots.get(m) for m in run["val"]}, "settings": s, "gates": protocol.get("gates")}
    return {**body, "address": H(body)}


def realization(recipe_addr, weights_sha256, env=None, evidence_root=None, protocol_id=None):
    body = {"level": "L2_realization", "parent": recipe_addr, "weights_sha256": weights_sha256, "env": env or {},
            "evidence_root": evidence_root, "protocol": protocol_id}
    return {**body, "address": H(body)}


def behaviour(realization_addr, metrics: dict, policy: dict):
    body = {"level": "L3_behaviour", "parent": realization_addr, "metrics": metrics, "policy": policy}
    return {**body, "address": H(body)}


def equivalent(b1, b2, policy):
    """Same recipe, metrics within the variance policy -> same knowledge."""
    tol = policy.get("abs", 0.0)
    diffs = {}
    for k in set(b1["metrics"]) & set(b2["metrics"]):
        a, b = b1["metrics"][k], b2["metrics"][k]
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            diffs[k] = round(abs(a - b), 6)
    worst = max(diffs.values()) if diffs else None
    return {"equivalent": worst is not None and worst <= tol, "max_diff": worst, "diffs": diffs, "policy": policy}
