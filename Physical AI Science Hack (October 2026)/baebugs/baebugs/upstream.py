"""Upstream BioKEA / hardware repos as chain-of-custody objects (pinned, not vendored).

Each upstream repo is mirrored on the data drive (never copied into this public repo: most have
no licence or GPL) and pinned by
  - its git commit (git's own Merkle DAG: commit -> tree -> blobs) and
  - a sha256 Merkle root over every tracked file at that commit (same construction as our
    dataset pointer manifests), so a file-level break can be located.
Pins are appended to daisy/upstream_mmr.jsonl; daisy/upstream.json holds the current pin table.
`check()` re-verifies a mirror against its pin (BREAK if the local bytes changed) and compares
the remote HEAD (DRIFT if upstream moved; a new pin is a new MMR leaf, never an overwrite).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

from .explore import merkle_root

REPOS = {  # name: (url, why it is in the custody graph)
    "BioKEA/BugPicker": ("https://github.com/BioKEA/BugPicker", "BugPicker module 3: vision pick-and-place, trays (GPL-3.0)"),
    "BioKEA/BugPicker-arm-demo": ("https://github.com/BioKEA/BugPicker-arm-demo", "arm demo for BugPicker (GPL-3.0)"),
    "BioKEA/BugSorter": ("https://github.com/BioKEA/BugSorter", "module 1: coarse size sorting (Track A target)"),
    "BioKEA/PlateReader": ("https://github.com/BioKEA/PlateReader", "plate reading downstream of picking"),
    "BioKEA/prompt-to-print": ("https://github.com/BioKEA/prompt-to-print", "Claude-for-CAD printing workflow (MIT)"),
    "zlite/B601": ("https://github.com/zlite/B601", "Seeed B601-DM arm demos, calibration, OAK camera mounts"),
    "zlite/disperser": ("https://github.com/zlite/disperser", "module 2: CoreXY bug disperser"),
    "zlite/entosieve": ("https://github.com/zlite/entosieve", "EntoSieve, predecessor of the BugSorter"),
    "zlite/liquid-handler": ("https://github.com/zlite/liquid-handler", "syringe end effector for SO-101 arm"),
    "zlite/liquid-handler-marlin": ("https://github.com/zlite/liquid-handler-marlin", "module 4: enzyme dispenser firmware + CAD"),
    "zlite/plate-gripper": ("https://github.com/zlite/plate-gripper", "plate gripper end effector (plate transport)"),
    "zlite/railprinter": ("https://github.com/zlite/railprinter", "rail motion between stations"),
}
MIRROR = Path("/Volumes/magicBLACKbox/baebugs/upstream")


def _git(args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def sha256_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def tree_manifest(repo_dir):
    """sha256 leaves over tracked files (path-bound: leaf = sha256(path NUL file_sha))."""
    files = sorted(_git(["ls-files", "-z"], repo_dir).split("\0")) if Path(repo_dir, ".git").exists() else []
    leaves, nbytes = [], 0
    for rel in filter(None, files):
        p = Path(repo_dir, rel)
        if not p.is_file():
            continue
        fs = sha256_file(p); nbytes += p.stat().st_size
        leaves.append({"path": rel, "sha256": fs, "leaf": hashlib.sha256(f"{rel}\0{fs}".encode()).hexdigest()})
    return leaves, (merkle_root(sorted(l["leaf"] for l in leaves)) if leaves else None), nbytes


def mirror(name, root=MIRROR):
    url = REPOS[name][0]; d = Path(root, name.replace("/", "__"))
    if (d / ".git").exists():
        _git(["fetch", "--quiet", "origin"], d)
        _git(["reset", "--quiet", "--hard", "origin/HEAD"], d)
    else:
        d.parent.mkdir(parents=True, exist_ok=True)
        _git(["clone", "--quiet", url, str(d)])
    return d


def pin(name, root=MIRROR, licence=None):
    d = Path(root, name.replace("/", "__"))
    leaves, sroot, nbytes = tree_manifest(d)
    return {"type": "upstream_pinned", "repo": name, "url": REPOS[name][0], "why": REPOS[name][1],
            "licence": licence, "commit": _git(["rev-parse", "HEAD"], d), "tree": _git(["rev-parse", "HEAD^{tree}"], d),
            "commit_time": _git(["log", "-1", "--format=%cI"], d), "files": len(leaves), "bytes": nbytes,
            "sha256_root": sroot, "mirror": str(d), "pinned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "vendored": False}


def check(p):
    """BREAK if the mirror's bytes no longer match the pin; DRIFT if upstream HEAD moved."""
    d = Path(p["mirror"]); out = {"repo": p["repo"], "pinned_commit": p["commit"][:12]}
    if not (d / ".git").exists():
        return {**out, "level": "BREAK", "reason": "mirror missing"}
    head = _git(["rev-parse", "HEAD"], d)
    if head != p["commit"]:
        return {**out, "level": "BREAK", "reason": f"mirror HEAD {head[:12]} != pinned"}
    _, sroot, _ = tree_manifest(d)
    if sroot != p["sha256_root"]:
        return {**out, "level": "BREAK", "reason": "file bytes changed (sha256 root mismatch)"}
    return {**out, "level": "OK", "reason": "mirror matches pin"}


def remote_drift(p):
    try:
        remote = subprocess.run(["git", "ls-remote", p["url"], "HEAD"], capture_output=True, text=True, timeout=20, check=False).stdout.split()
    except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
        return {"repo": p["repo"], "level": "WARN", "reason": f"remote unreachable: {e}"}
    if not remote:
        return {"repo": p["repo"], "level": "WARN", "reason": "remote HEAD unknown"}
    if remote[0] != p["commit"]:
        return {"repo": p["repo"], "level": "DRIFT", "reason": f"upstream moved to {remote[0][:12]}; re-pin to adopt"}
    return {"repo": p["repo"], "level": "OK", "reason": "upstream == pin"}


def pin_all(repo=".", licences=None):
    from .mmr import MMRLog
    licences = licences or {}
    table, log = {}, MMRLog(Path(repo, "daisy/upstream_mmr.jsonl"))
    prev = json.loads(Path(repo, "daisy/upstream.json").read_text()) if Path(repo, "daisy/upstream.json").exists() else {}
    for name in REPOS:
        mirror(name)
        p = pin(name, licence=licences.get(name))
        old = prev.get(name)
        if not old or old["commit"] != p["commit"] or old["sha256_root"] != p["sha256_root"]:
            log.append({**p, "supersedes": old and {"commit": old["commit"], "sha256_root": old["sha256_root"]}})
        table[name] = p
        print(name, p["commit"][:12], p["files"], "files", (p["sha256_root"] or "")[:12], flush=True)
    Path(repo, "daisy/upstream.json").write_text(json.dumps(table, indent=1, sort_keys=True))
    return table, log.mmr.root


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser("baebugs-upstream")
    ap.add_argument("cmd", choices=["pin", "check"])
    ap.add_argument("--licences", help="json {repo: spdx}")
    a = ap.parse_args()
    if a.cmd == "pin":
        print(pin_all(".", json.loads(Path(a.licences).read_text()) if a.licences else None)[1])
    else:
        t = json.loads(Path("daisy/upstream.json").read_text())
        for p in t.values():
            print(json.dumps(check(p)), json.dumps(remote_drift(p)))
