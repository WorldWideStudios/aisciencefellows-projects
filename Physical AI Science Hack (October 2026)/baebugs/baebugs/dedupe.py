"""Merkle dedupe with pointer files.

Every file is addressed by its sha256. For each set of byte-identical files one
CANONICAL copy is kept (preferring paths under KEEP roots); every other copy can be
replaced by a small pointer file `<name>.ptr.json`:

  {schema, sha256, size, canonical (relative to base), index_root, proof}

`index_root` is the Merkle root over the sorted unique content hashes, and `proof`
is the inclusion proof of this file's hash in that root, so any model or person can
check the pointer without trusting the path. Hardlinked copies (same inode) are already
deduplicated on disk and are never counted as savings.

Nothing is lost: `materialize` copies the canonical bytes back and re-checks the hash.
`apply` only replaces a copy after re-hashing both it and its canonical, and it writes the
pointer before removing the copy.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .explore import merkle_root
from .hybrid import merkle_proof, verify_merkle
from .retention import sha

SCHEMA = "baebugs.ptr.v1"
SUFFIX = ".ptr.json"


def scan(roots, base):
    """{sha: [{path, size, inode}]} over regular files (pointer files skipped)."""
    base = Path(base)
    seen_inode, idx = {}, {}
    for r in roots:
        for f in sorted(Path(r).rglob("*")):
            if not f.is_file() or f.is_symlink() or f.name.endswith(SUFFIX):
                continue
            st = f.stat()
            key = (st.st_dev, st.st_ino)
            h = seen_inode.get(key) or sha(f)
            seen_inode[key] = h
            idx.setdefault(h, []).append({"path": str(f.relative_to(base)), "size": st.st_size, "inode": st.st_ino})
    return idx


def plan(roots, base, keep_prefixes=()):
    """Pick canonical copies; list copies that would become pointers."""
    idx = scan(roots, base)
    leaves = sorted(idx)
    root = merkle_root(leaves) if leaves else None
    items, saved = [], 0
    for h, locs in idx.items():
        rank = lambda l: (not any(l["path"].startswith(p) for p in keep_prefixes), l["path"])
        locs = sorted(locs, key=rank)
        canon = locs[0]
        counted = {canon["inode"]}
        for l in locs[1:]:
            if l["inode"] == canon["inode"]:          # already a hardlink of the canonical
                continue
            # every path of a non-canonical inode is relinked (otherwise the old inode survives
            # through its other links); its bytes are counted once
            items.append({"sha256": h, "size": l["size"], "path": l["path"], "canonical": canon["path"]})
            if l["inode"] not in counted:
                counted.add(l["inode"]); saved += l["size"]
    return {"base": str(base), "index_root": root, "unique": len(leaves),
            "files": sum(len(v) for v in idx.values()), "pointers": len(items),
            "bytes_saved": saved, "items": items, "_leaves": leaves}


def pointer(item, index_root, leaves):
    return {"schema": SCHEMA, "sha256": item["sha256"], "size": item["size"], "canonical": item["canonical"],
            "index_root": index_root, "proof": merkle_proof(leaves, leaves.index(item["sha256"]))}


def apply(p, limit=None, mode="pointer", ledger=None):
    """Replace copies. Re-hashes copy and canonical before each replacement.
    mode="pointer": copy -> `<name>.ptr.json` (cold storage; materialize to use).
    mode="link":    copy -> hardlink to the canonical (tools still read a normal file);
                    the pointer record goes to a jsonl ledger instead of a sidecar."""
    base, done, skipped = Path(p["base"]), [], []
    led = Path(ledger or base / "dedupe_pointers.jsonl")
    for it in p["items"][:limit]:
        f, c = base / it["path"], base / it["canonical"]
        if not (f.exists() and c.exists()) or sha(f) != it["sha256"] or sha(c) != it["sha256"]:
            skipped.append(it["path"]); continue
        if mode == "link":
            tmp = f.with_name(f.name + ".dedupe_tmp")
            os.link(c, tmp); os.replace(tmp, f)
            if f.stat().st_ino != c.stat().st_ino or sha(f) != it["sha256"]:
                skipped.append(it["path"]); continue
            with led.open("a") as fh:
                fh.write(json.dumps({**pointer(it, p["index_root"], p["_leaves"]), "path": it["path"], "mode": "link"}) + "\n")
            done.append(it["path"]); continue
        ptr = f.with_name(f.name + SUFFIX)
        ptr.write_text(json.dumps(pointer(it, p["index_root"], p["_leaves"]), indent=1))
        if verify(ptr, base)["ok"]:
            f.unlink(); done.append(it["path"])
        else:
            ptr.unlink(); skipped.append(it["path"])
    return {"replaced": len(done), "skipped": skipped}


def verify(ptr, base):
    d = json.loads(Path(ptr).read_text())
    c = Path(base, d["canonical"])
    proof_ok = verify_merkle(d["sha256"], d["proof"], d["index_root"])
    bytes_ok = c.exists() and sha(c) == d["sha256"]
    return {"ok": proof_ok and bytes_ok, "proof_ok": proof_ok, "canonical_ok": bytes_ok}


def materialize(ptr, base):
    """Turn a pointer back into the full file (hash-checked)."""
    ptr = Path(ptr); d = json.loads(ptr.read_text())
    out = ptr.with_name(ptr.name[: -len(SUFFIX)])
    shutil.copy2(Path(base, d["canonical"]), out)
    if sha(out) != d["sha256"]:
        out.unlink(); raise ValueError(f"hash mismatch materializing {out}")
    ptr.unlink()
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-dedupe")
    ap.add_argument("base"); ap.add_argument("roots", nargs="+")
    ap.add_argument("--keep", nargs="*", default=[], help="path prefixes preferred as canonical")
    ap.add_argument("--out", required=True); ap.add_argument("--apply", action="store_true")
    ap.add_argument("--mode", choices=["pointer", "link"], default="pointer")
    ap.add_argument("--only", nargs="*", default=None, help="apply only to copies under these prefixes")
    a = ap.parse_args(argv)
    p = plan(a.roots, a.base, a.keep)
    if a.only is not None:
        p["items"] = [i for i in p["items"] if any(i["path"].startswith(o) for o in a.only)]
    rep = {k: v for k, v in p.items() if not k.startswith("_")}
    rep["bytes_saved_selected"] = sum(i["size"] for i in p["items"])
    if a.apply:
        rep["applied"] = apply(p, mode=a.mode)
    Path(a.out).write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "items"}, indent=1)[:2000])


if __name__ == "__main__":
    main()
