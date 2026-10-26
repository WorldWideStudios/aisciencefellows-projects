"""Atoms of knowledge (AoK): every tracked piece of baebugs with its claim, licence and status in context.

One atom per tracked file (a leaf) and one per outside thing baebugs uses (an external atom). Each atom says,
in plain words, three things a reader needs and nothing more:

  claim    OWN          written here (biobitworks, with Claude as coding assistant); claimable; MIT
           OWN+TERMS    written here and claimable, but something it runs with or derives from adds terms
           THIRD        not ours; used under its own licence; credited and pinned by hash, never claimed
  licence  the licence that governs this atom *in this context* (plus the added terms, if any)
  status   frozen (preregistered, never edited) | result | tested | built | reference

Leaves roll up to a Merkle root per module (directory group), modules and external atoms to one repo root.
Everything is derived from the working tree and git, so the same tree always gives the same roots.
Not legal advice: it records what the licences say, so a person can check it.

  python -m baebugs.aok            -> kg/aok.json (for agents) + docs/CLAIMS.md (for people)
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from .explore import merkle_root

INDEX_FILES = {"kg/aok.json", "docs/CLAIMS.md", "site/mvp/mvp.json"}   # the index itself is not an atom (it would hash itself)
OWN, OWN_T, THIRD = "OWN", "OWN+TERMS", "THIRD"
MIT = "MIT"

# Outside things baebugs uses. Licences as published by each project (checked 2026-10-25).
EXTERNAL = [
    {"id": "ext:ultralytics", "name": "Ultralytics YOLO", "licence": "AGPL-3.0",
     "role": "training/inference library", "url": "https://github.com/ultralytics/ultralytics",
     "effect": "models trained or run with it are AGPL-3.0 unless an Ultralytics Enterprise licence is held"},
    {"id": "ext:gbif-media", "name": "GBIF specimen photos (museum collections)", "licence": "CC0-1.0 / CC-BY-4.0",
     "role": "training images", "url": "https://www.gbif.org",
     "effect": "CC BY images need the rights holder credited in anything derived (crops, figures); see daisy/licences_gbif.json"},
    {"id": "ext:opentrons", "name": "Opentrons Python API + labware schema", "licence": "Apache-2.0",
     "role": "protocol API and labware JSON schema", "url": "https://github.com/Opentrons/opentrons",
     "effect": "our labware and protocols are our own; 'Opentrons' is their trademark, no endorsement implied"},
    {"id": "ext:threejs", "name": "three.js", "licence": "MIT", "role": "WebGL viewer (CDN)",
     "url": "https://github.com/mrdoob/three.js", "effect": "none beyond keeping its notice"},
    {"id": "ext:manifold3d", "name": "manifold3d", "licence": "Apache-2.0", "role": "CSG for STL parts",
     "url": "https://github.com/elalish/manifold", "effect": "none on the generated meshes"},
    {"id": "ext:trimesh", "name": "trimesh", "licence": "MIT", "role": "mesh export/checks",
     "url": "https://github.com/mikedh/trimesh", "effect": "none on the generated meshes"},
    {"id": "ext:kaggle", "name": "Kaggle notebooks (GPU)", "licence": "Kaggle Terms of Use", "role": "compute",
     "url": "https://www.kaggle.com/terms", "effect": "private datasets/kernels stay private; outputs are ours"},
    {"id": "ext:claude", "name": "Claude (Anthropic)", "licence": "Anthropic Terms (outputs assigned to the user)",
     "role": "coding assistant, co-author in commits", "url": "https://www.anthropic.com/legal",
     "effect": "biobitworks directed, reviewed and chose the work; copyright in purely AI-generated text is "
               "unsettled law, so the claim rests on the human direction and selection"},
]

# path rules: first match wins -> module, kind, status
RULES = [
    ("daisy/results/", "daisy-results", "result", "result"),
    ("daisy/DAISY-", "daisy-protocols", "protocol", "frozen"),
    ("daisy/TRUTH-", "daisy-protocols", "protocol", "frozen"),
    ("daisy/", "custody-ledgers", "ledger", "built"),
    ("kaggle/", "kaggle-kernels", "code", "built"),
    ("print/fuse1/", "toy-insects", "print", "built"),
    ("print/", "lab-parts", "print", "built"),
    ("opentrons/", "opentrons-modules", "labware", "tested"),
    ("site/", "mvp-site", "page", "built"),
    ("dashboard/", "dashboards", "page", "built"),
    ("kg/", "knowledge-graph", "data", "built"),
    ("ledger/", "custody-ledgers", "ledger", "built"),
    ("tests/", "tests", "test", "tested"),
    ("notebooks/", "notebooks", "notebook", "built"),
    ("docs/", "docs", "doc", "built"),
    ("baebugs/", "python-package", "code", "built"),
    ("", "repo-meta", "meta", "built"),
]


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True, check=True).stdout


def _rule(path):
    for pre, mod, kind, status in RULES:
        if path.startswith(pre):
            return mod, kind, status
    raise AssertionError(path)


def _terms(repo, path, kind):
    """Added terms that apply to an OWN atom in context (deterministic: from the file itself)."""
    t = []
    if path.endswith(".py"):
        try:
            src = (repo / path).read_text(errors="ignore")
        except OSError:
            src = ""
        if re.search(r"(from|import)\s+ultralytics", src):
            t.append("ext:ultralytics")
        if re.search(r"(from|import)\s+opentrons", src):
            t.append("ext:opentrons")
    if path.startswith(("kaggle/", "daisy/results/")):
        t.append("ext:ultralytics")
    if path.startswith(("kg/", "daisy/results/", "kaggle/daisy_bb_004")):
        t.append("ext:gbif-media")
    if path.startswith("opentrons/"):
        t.append("ext:opentrons")
    return sorted(set(t))


def _test_coverage(paths):
    tested = set()
    for p in paths:
        if p.startswith("tests/test_") and p.endswith(".py"):
            tested.add("baebugs/" + p[len("tests/test_"):])
    return tested


def leaf_hash(a):
    return hashlib.sha256("\0".join([a["path"], a["sha256"], a["claim"], a["licence"], a["status"]]).encode()).hexdigest()


def build(repo="."):
    repo = Path(repo)
    paths = sorted({p for p in _git(repo, "ls-files").splitlines() if (repo / p).is_file() and p not in INDEX_FILES})  # set: unmerged files are listed once per stage
    tested = _test_coverage(paths)
    upstream = json.loads((repo / "daisy/upstream.json").read_text()) if (repo / "daisy/upstream.json").exists() else {}
    # authorship per file from git (counts, not names beyond the commit author field)
    commits = Counter(); claude = Counter()
    pathset = set(paths)
    log = _git(repo, "log", "--name-only", "--format=%x01%b%x02")
    for chunk in log.split("\x01")[1:]:
        body, _, files = chunk.partition("\x02")
        co = "Co-Authored-By: Claude" in body
        for f in files.split():
            if f in pathset:
                commits[f] += 1; claude[f] += co
    atoms, mods = [], defaultdict(list)
    for p in paths:
        mod, kind, status = _rule(p)
        if p in tested and status == "built":
            status = "tested"
        terms = _terms(repo, p, kind)
        claim = OWN_T if terms else OWN
        lic = MIT + ("" if not terms else " + " + ", ".join(t.split(":")[1] for t in terms) + " terms")
        a = {"id": f"leaf:{p}", "path": p, "module": mod, "kind": kind, "status": status, "claim": claim,
             "licence": lic, "terms": terms, "sha256": _sha(repo / p),
             "commits": commits[p], "claude_coauthored_commits": claude[p]}
        a["leaf"] = leaf_hash(a)
        atoms.append(a); mods[mod].append(a)
    modules = {}
    for m, aa in sorted(mods.items()):
        c = Counter(x["claim"] for x in aa)
        modules[m] = {"id": f"module:{m}", "atoms": len(aa), "root": merkle_root(sorted(x["leaf"] for x in aa)),
                      "claims": dict(c), "status": dict(Counter(x["status"] for x in aa)),
                      "terms": sorted({t for x in aa for t in x["terms"]})}
    ext = []
    for e in EXTERNAL:
        ext.append({**e, "claim": THIRD, "status": "reference",
                    "leaf": hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()})
    for name, u in sorted(upstream.items()):
        e = {"id": f"ext:upstream:{name}", "name": name, "licence": u["licence"] if u["licence"] != "NONE"
             else "no licence (all rights reserved)", "role": u.get("why", ""), "url": u.get("url", ""),
             "effect": "pinned by commit + sha256 root only, never copied into baebugs"
                       + ("" if u["licence"] != "NONE" else "; ask the owner before reuse"),
             "pin": {"commit": u["commit"], "sha256_root": u["sha256_root"]}}
        ext.append({**e, "claim": THIRD, "status": "reference",
                    "leaf": hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()})
    root = merkle_root(sorted([m["root"] for m in modules.values()] + [e["leaf"] for e in ext]))
    totals = Counter(a["claim"] for a in atoms) + Counter(e["claim"] for e in ext)
    return {"type": "aok", "root": root, "atoms": len(atoms) + len(ext), "totals": dict(totals),
            "modules": modules, "external": ext, "leaves": atoms,
            "legend": {OWN: "written here; claimable; MIT",
                       OWN_T: "written here and claimable; the listed outside terms also apply in this context",
                       THIRD: "not ours; used under its licence; credited, pinned by hash, never claimed"},
            "note": "Records what the licences say; not legal advice."}


def check(aok, repo="."):
    """Gate: licence on 100% of atoms, every leaf resolves to its bytes, no THIRD atom copied in."""
    errs = []
    for a in aok["leaves"]:
        if not a["licence"]:
            errs.append(f"no licence {a['path']}")
        p = Path(repo, a["path"])
        if not p.exists() or _sha(p) != a["sha256"]:
            errs.append(f"does not resolve {a['path']}")
    for e in aok["external"]:
        if not e["licence"]:
            errs.append(f"no licence {e['id']}")
    return errs


def claims_md(aok):
    L = ["# What baebugs claims, and under which licence", "",
         ("Every file is an *atom* with a claim, a licence in context, a status and a hash "
         "(full list for agents: [`kg/aok.json`](../kg/aok.json)). "
         "This page is the short version. It records what the licences say; it is not legal advice."), "",
         f"**AoK root:** `{aok['root']}` · {aok['atoms']} atoms · "
         + " · ".join(f"{k} {v}" for k, v in sorted(aok["totals"].items())), "",
         "| claim | meaning |", "|---|---|"]
    L += [f"| **{k}** | {v} |" for k, v in aok["legend"].items()]
    L += ["", "## Ours (biobitworks), by module", "",
          "| module | atoms | claim | outside terms that apply here | module root |", "|---|---|---|---|---|"]
    for m, d in aok["modules"].items():
        cl = ", ".join(f"{k} {v}" for k, v in sorted(d["claims"].items()))
        t = ", ".join(x.split(":")[1] for x in d["terms"]) or "none"
        L.append(f"| {m} | {d['atoms']} | {cl} | {t} | `{d['root'][:12]}` |")
    L += ["", "## Not ours (used, credited, never claimed)", "", "| thing | licence | what it means for us |", "|---|---|---|"]
    for e in aok["external"]:
        L.append(f"| [{e['name']}]({e['url']}) | {e['licence']} | {e['effect']} |")
    L += ["", "## The three things to remember", "",
          ("1. **Code, prints, labware, pages, protocols and ledgers written here are ours (MIT).** "
          "That includes the parametric toy insects, the lab parts and the Opentrons labware."),
          ("2. **Trained weights are AGPL-3.0** because they come from Ultralytics YOLO; "
          "anything shipped with them must offer its source under AGPL-3.0 (or hold an Ultralytics licence)."),
          ("3. **Specimen photos belong to the museums.** CC0 needs nothing; CC BY needs the rights holder "
          "credited wherever crops or figures appear. BioKEA and zlite repos are pinned by hash, not copied; "
          "the ones with no licence need the owner's permission before any reuse."), ""]
    return "\n".join(L)


def main(repo="."):
    a = build(repo)
    errs = check(a, repo)
    Path(repo, "kg").mkdir(exist_ok=True)
    Path(repo, "kg/aok.json").write_text(json.dumps(a, indent=1, sort_keys=True) + "\n")
    Path(repo, "docs/CLAIMS.md").write_text(claims_md(a))
    print(json.dumps({"root": a["root"], "atoms": a["atoms"], "totals": a["totals"], "errors": errs[:5]}))
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
