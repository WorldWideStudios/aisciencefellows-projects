"""Merkle Mountain Range: append-only, every past state provable.

Leaves are appended forever; equal-height peaks merge. The root bags the peaks
right to left. Any leaf has an inclusion proof against any later root, so an
evaluation recorded today can be shown, later, to be part of history unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _h(a: str, b: str) -> str:
    return hashlib.sha256(bytes.fromhex(a) + bytes.fromhex(b)).hexdigest()


class MMR:
    def __init__(self, leaves=None):
        self.leaves = []
        self.peaks = []           # [(height, hash)]
        for l in leaves or []:
            self.append(l)

    def append(self, leaf_hex: str) -> int:
        self.leaves.append(leaf_hex)
        self.peaks.append((0, leaf_hex))
        while len(self.peaks) >= 2 and self.peaks[-1][0] == self.peaks[-2][0]:
            (h, r), (_, l) = self.peaks.pop(), self.peaks.pop()
            self.peaks.append((h + 1, _h(l, r)))
        return len(self.leaves) - 1

    @staticmethod
    def bag(peaks):
        if not peaks:
            return None
        acc = peaks[-1][1]
        for _, p in reversed(peaks[:-1]):
            acc = _h(p, acc)
        return acc

    @property
    def root(self):
        return self.bag(self.peaks)

    def _mountains(self):
        """Leaf index ranges of each peak (left to right)."""
        out, start = [], 0
        for h, _ in self.peaks:
            out.append((start, start + 2 ** h, h)); start += 2 ** h
        return out

    def proof(self, i):
        """Siblings from leaf i up to its peak, plus every peak (for bagging)."""
        for s, e, h in self._mountains():
            if s <= i < e:
                level = self.leaves[s:e]
                idx, path = i - s, []
                while len(level) > 1:
                    sib = idx ^ 1
                    path.append(("L" if sib < idx else "R", level[sib]))
                    level = [_h(level[k], level[k + 1]) for k in range(0, len(level), 2)]
                    idx //= 2
                return {"leaf": self.leaves[i], "index": i, "path": path, "peaks": [p for _, p in self.peaks],
                        "peak_index": [m[0] for m in self._mountains()].index(s), "size": len(self.leaves)}
        raise IndexError(i)

    @staticmethod
    def verify(proof, root):
        acc = proof["leaf"]
        for side, sib in proof["path"]:
            acc = _h(sib, acc) if side == "L" else _h(acc, sib)
        if acc != proof["peaks"][proof["peak_index"]]:
            return False
        return MMR.bag([(0, p) for p in proof["peaks"]]) == root


class MMRLog:
    """jsonl-backed MMR: each line = {"index", "leaf", "root", "record"}."""

    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.mmr = MMR()
        self.records = []
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    self.mmr.append(r["leaf"]); self.records.append(r)

    def append(self, record: dict):
        leaf = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
        i = self.mmr.append(leaf)
        row = {"index": i, "leaf": leaf, "root": self.mmr.root, "record": record}
        with self.path.open("a") as f:
            f.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        self.records.append(row)
        return row

    def verify(self):
        m = MMR()
        for r in self.records:
            leaf = hashlib.sha256(json.dumps(r["record"], sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
            if leaf != r["leaf"]:
                return False, r["index"]
            m.append(leaf)
            if m.root != r["root"]:
                return False, r["index"]
        return True, None
