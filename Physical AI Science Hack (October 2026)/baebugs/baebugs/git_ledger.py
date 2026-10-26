"""Merkle ledger that commits and pushes at every break point.

Every pipeline step (data pull, pseudo-labelling, dataset mix, each training
epoch, benchmark) appends a leaf = sha256(record). The file's Merkle root is
recomputed and the ledger is committed and pushed to GitHub immediately, so the
repo history *is* the chain of break points: any later claim can be checked
against the commit whose root covers it. Weights are recorded by sha256 (too
large to push every epoch); the files stay on the data drive.

Git failures never stop training: they are logged and retried on the next leaf.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

from .explore import merkle_root


def sha256_file(path, chunk=1 << 20) -> str | None:
    p = Path(path)
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


class GitLedger:
    def __init__(self, run: str, repo_dir, push=True, remote="origin", branch="main"):
        self.repo = Path(repo_dir)
        self.path = self.repo / "ledger" / f"{run}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run, self.push, self.remote, self.branch = run, push, remote, branch

    def leaves(self):
        if not self.path.exists():
            return []
        return [json.loads(l)["leaf"] for l in self.path.read_text().splitlines() if l.strip()]

    def _git(self, *args, check=False):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True,
                              text=True, check=check)

    def append(self, step: str, payload: dict | None = None, files: dict | None = None) -> dict:
        rec = {"t": time.time(), "run": self.run, "step": step, "payload": payload or {},
               "files": {k: sha256_file(v) for k, v in (files or {}).items()}}
        rec["leaf"] = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
        leaves = self.leaves() + [rec["leaf"]]
        rec["n"] = len(leaves)
        rec["root"] = merkle_root(leaves)
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        self._commit(rec)
        return rec

    def _commit(self, rec):
        rel = str(self.path.relative_to(self.repo))
        self._git("add", rel)
        msg = (f"BP {self.run} #{rec['n']} {rec['step']} root {rec['root'][:12]}\n\n"
               + json.dumps(rec["payload"], default=str)[:1500]
               + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
        c = self._git("-c", "user.name=biobitworks", "-c", "user.email=biobitworks@gmail.com",
                      "commit", "-q", "-m", msg, "--", rel)
        if c.returncode != 0 or not self.push:
            return
        for _ in range(3):
            self._git("pull", "-q", "--rebase", "--autostash", self.remote, self.branch)
            if self._git("push", "-q", self.remote, self.branch).returncode == 0:
                return
            time.sleep(3)
        (self.path.parent / "push_failures.log").open("a").write(f"{time.ctime()} {rec['leaf']}\n")

    def verify(self) -> bool:
        recs = [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]
        leaves = []
        for r in recs:
            body = {k: v for k, v in r.items() if k not in ("leaf", "n", "root")}
            if hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest() != r["leaf"]:
                return False
            leaves.append(r["leaf"])
            if merkle_root(leaves) != r["root"]:
                return False
        return True


def yolo_epoch_callback(ledger: GitLedger):
    """Ultralytics on_fit_epoch_end hook: one break point per epoch."""
    def cb(trainer):
        m = {k: round(float(v), 5) for k, v in (trainer.metrics or {}).items()}
        e = trainer.epoch + 1
        # ultralytics re-fires this hook for the final validation of best.pt
        step = f"epoch_{e:03d}" if e <= trainer.epochs else "final_val"
        ledger.append(step,
                      {"epoch": trainer.epoch + 1, "epochs": trainer.epochs, "metrics": m,
                       "fitness": float(getattr(trainer, "fitness", 0) or 0)},
                      files={"last.pt": Path(trainer.wdir) / "last.pt",
                             "best.pt": Path(trainer.wdir) / "best.pt"})
    return cb
