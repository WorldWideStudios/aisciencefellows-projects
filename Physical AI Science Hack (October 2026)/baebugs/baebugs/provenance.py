"""FAIR-by-construction provenance: every step appends a record (what, to which
specimen/sample, with which parameters, image hashes, software version) and each
record carries the hash of the previous one, so the chain can be verified and a
published claim traced back to raw images without a write-up afterwards."""
from __future__ import annotations

import hashlib
import json
import platform
import time
from pathlib import Path

from . import __version__


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())


class Provenance:
    def __init__(self, path="runs/provenance.jsonl", instrument="baebugs"):
        self.path = Path(path)
        self.instrument = instrument
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _last_hash(self):
        if not self.path.exists():
            return "0" * 64
        lines = self.path.read_text().strip().splitlines()
        return json.loads(lines[-1])["hash"] if lines else "0" * 64

    def record(self, step: str, sample_id: str, params: dict | None = None,
               inputs: dict | None = None, outputs: dict | None = None):
        rec = {"t": time.time(), "instrument": self.instrument, "step": step,
               "sample_id": sample_id, "params": params or {},
               "inputs": inputs or {}, "outputs": outputs or {},
               "software": {"baebugs": __version__, "python": platform.python_version()},
               "prev": self._last_hash()}
        body = json.dumps(rec, sort_keys=True, default=str)
        rec["hash"] = sha256_bytes(body.encode())
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        return rec

    def verify(self) -> bool:
        prev = "0" * 64
        for line in self.path.read_text().strip().splitlines():
            rec = json.loads(line)
            h = rec.pop("hash")
            if rec["prev"] != prev or sha256_bytes(
                    json.dumps(rec, sort_keys=True, default=str).encode()) != h:
                return False
            prev = h
        return True

    def trace(self, sample_id: str):
        return [json.loads(l) for l in self.path.read_text().splitlines()
                if json.loads(l)["sample_id"] == sample_id]
