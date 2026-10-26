"""Commit-and-push watcher (runs on magicstudio or magicpro), with a small local model writing the summary.

Every `--every` seconds, if allowed paths changed (run outputs, ledgers, graph packs, docs):
  1. regenerate the atoms (kg/aok.json) and the graph pack (site/mvp/mvp.json)
  2. gate: the AoK and MVP tests must pass, otherwise nothing is committed (fail closed)
  3. ask a local model for a one-line summary of the diffstat: Ollarma (127.0.0.1:8484 /chat) if it is up,
     else Ollama directly (127.0.0.1:11434). If neither answers, a deterministic summary is used.
  4. commit on the working branch only (never main), pull, push
  5. append a receipt to daisy/watcher_mmr.jsonl: diffstat sha, model, prompt sha, response sha, commit, roots

Model output varies run to run; that is fine because every step is hashed in the receipt.
  python -m baebugs.watch_commit --every 600            (Ctrl-C to stop; nothing persistent is installed)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ALLOW = ["daisy/", "kg/", "site/mvp/", "docs/", "dashboard/csv/", "dashboard/data/"]
MODEL = "qwen2.5-coder:1.5b"


def _git(*a, check=True):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=check).stdout


def _h(s):
    return hashlib.sha256(s.encode()).hexdigest()


def _post(url, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # local services only
        return json.loads(r.read())


def summarise(diffstat, model=MODEL):
    prompt = ("Write one short git commit subject (max 70 chars, no quotes). Say only which files were added or "
              "updated, using the file names below; do not guess reasons or invent work. Files:\n" + diffstat[:3000])
    for name, call in (
        ("ollarma", lambda: _post("http://127.0.0.1:8484/chat", {"message": prompt, "model": model}).get("response")),
        ("ollama", lambda: _post("http://127.0.0.1:11434/api/generate", {"model": model, "prompt": prompt, "stream": False,
                                                                       "options": {"temperature": 0, "seed": 0}})["response"]),
    ):
        try:
            text = (call() or "").strip().splitlines()[0].strip().strip('"')[:70]
            if text:
                return text, name, prompt
        except Exception:  # noqa: BLE001,S112 - try the next route
            continue
    n = len([line for line in diffstat.splitlines() if "|" in line])
    return f"update {n} file(s) under {', '.join(sorted({p.split('/')[0] for p in ALLOW}))}", "deterministic", prompt


def once(branch_guard=True, push=True):
    br = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    if branch_guard and br in ("main", "master"):
        return {"skipped": f"on {br}; the watcher never commits to main"}
    changed = [line[3:] for line in _git("status", "--porcelain").splitlines() if any(line[3:].startswith(a) for a in ALLOW)]
    if not changed:
        return {"skipped": "nothing changed"}
    py = sys.executable
    for mod in ("baebugs.aok", "baebugs.mvp"):
        subprocess.run([py, "-m", mod], capture_output=True, check=False)
    t = subprocess.run([py, "-m", "pytest", "-q", "tests/test_aok.py", "tests/test_mvp.py"], capture_output=True, text=True, check=False)
    if t.returncode != 0:
        return {"skipped": "gate failed (AoK/MVP tests); nothing committed", "tail": t.stdout[-400:]}
    _git("add", "--", *ALLOW)
    stat = _git("diff", "--cached", "--stat")
    if not stat.strip():
        return {"skipped": "nothing staged"}
    subject, route, prompt = summarise(stat)
    pack = json.loads(Path("site/mvp/mvp.json").read_text())
    msg = f"watcher: {subject}\n\n{stat}\nWatcher: baebugs.watch_commit via {route} ({MODEL if route != 'deterministic' else 'no model'})\n"
    _git("commit", "-q", "-m", msg)
    sha = _git("rev-parse", "HEAD").strip()
    if push:
        _git("pull", "-q", "--no-rebase", "origin", br, check=False)
        _git("push", "-q", "origin", br, check=False)
    from .mmr import MMRLog
    rec = {"type": "watcher_commit", "commit": sha, "branch": br, "diffstat_sha256": _h(stat), "route": route, "model": MODEL,
           "prompt_sha256": _h(prompt), "response_sha256": _h(subject), "subject": subject, "mvp_root": pack["root"],
           "aok_root": pack["roots"]["aok"], "t": round(time.time(), 3)}
    MMRLog(Path("daisy/watcher_mmr.jsonl")).append(rec)   # receipt goes into the next commit
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=int, default=600); ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)
    while True:
        print(json.dumps(once(push=not a.no_push))[:400], flush=True)
        if a.once:
            return 0
        time.sleep(a.every)


if __name__ == "__main__":
    raise SystemExit(main())
