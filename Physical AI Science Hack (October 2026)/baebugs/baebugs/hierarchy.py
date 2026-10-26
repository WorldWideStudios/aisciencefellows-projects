"""Hierarchical sorting as nested partitions, each a Merkle tree (the sorter as an abstraction of
biological hierarchy sorting).

Physical and biological sorting share one shape: a coarse partition refined level by level, each
level only splitting its parent's groups (gravity / sieve size classes -> morphology -> DNA barcode
-> expression; or order -> family -> genus -> species). Here every level is a function
member -> label (or None = cannot place). The tree:
  node = {level, label, members, children};  hash = H(level, label, sorted member ids, sorted child hashes)
so the root commits to every assignment at every level, and any change is a located break point.

  leave_one_level_out  rebuild without one level; the leaf groups that merge are exactly what that
                       level contributes (differential analysis over the hierarchy)
  novelty              a member a level cannot place (label None, or below that level's confidence
                       threshold) is queued for expert review; an expert attestation adds the label
                       and the tree re-hashes (the old root stays in the MMR as the predecessor)
"""
from __future__ import annotations

import hashlib
import json

UNPLACED = "?"


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def build(members, levels, _depth=0, _label="root"):
    """members: list of dicts with "id". levels: list of (name, fn) with fn(member) -> label | None
    or (label, confidence). Returns the node tree and a novelty queue."""
    node = {"level": "root" if _depth == 0 else levels[_depth - 1][0], "label": _label,
            "members": sorted(m["id"] for m in members), "children": []}
    novel = []
    if _depth < len(levels):
        name, fn = levels[_depth]
        groups = {}
        for m in members:
            out = fn(m)
            lab, conf = (out if isinstance(out, tuple) else (out, 1.0))
            thr = m.get("_thr", {}).get(name, 0.0)
            if lab is None or conf < thr:
                novel.append({"id": m["id"], "level": name, "proposed": lab, "confidence": conf})
                lab = UNPLACED
            groups.setdefault(lab, []).append(m)
        for lab in sorted(groups):
            child, nv = build(groups[lab], levels, _depth + 1, lab)
            node["children"].append(child); novel += nv
    node["hash"] = H({k: node[k] for k in ("level", "label", "members")} | {"children": sorted(c["hash"] for c in node["children"])})
    return node, novel


def leaves(node, path=()):
    p = path + ((node["level"], node["label"]),) if node["level"] != "root" else path
    if not node["children"]:
        return {p: node["members"]}
    out = {}
    for c in node["children"]:
        out.update(leaves(c, p))
    return out


def partition(node):
    return sorted(tuple(v) for v in leaves(node).values())


def leave_one_level_out(members, levels):
    """For each level: how many final groups merge when it is removed (its contribution)."""
    full, _ = build(members, levels)
    base = partition(full)
    out = {"full_groups": len(base), "root": full["hash"], "levels": {}}
    for i, (name, _) in enumerate(levels):
        t, _ = build(members, levels[:i] + levels[i + 1:])
        p = partition(t)
        out["levels"][name] = {"groups_without": len(p), "groups_lost": len(base) - len(p),
                               "identical_partition": p == base, "root_without": t["hash"]}
    return out


def attest_label(member, level, label, expert_id):
    """Expert confirmation: pin the label for that level (content-addressed attestation)."""
    att = {"type": "expert_label", "member": member["id"], "level": level, "label": label, "expert": expert_id}
    member.setdefault("expert", {})[level] = {**att, "id": H(att)}
    return member["expert"][level]


def with_expert(fn, level):
    """Wrap a level function so expert labels override model output (confidence 1.0)."""
    def g(m):
        e = m.get("expert", {}).get(level)
        return (e["label"], 1.0) if e else fn(m)
    return g
