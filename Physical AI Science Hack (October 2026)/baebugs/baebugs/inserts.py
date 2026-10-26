"""Reusable tray frame + replaceable stainless filter inserts, each a custody object.

One printed/wood tray frame takes any insert; the insert (not the frame) carries the aperture. Each
physical insert has a durable identifier (engraved / tagged serial) and its own append-only history
in an MMR: received -> measured (actual aperture) -> deburred / cleaned -> used (run id) -> retired.
The insert's design id hashes its specification; its serial id hashes design id + serial, so two
cuts of the same design are distinct objects with the same design.

Status ladder (never skipped): CONCEPT -> RECEIVED -> MEASURED -> QUALIFIED -> IN_SERVICE -> RETIRED.
QUALIFIED requires a measured aperture within tolerance of nominal, deburred edges, a cleaning
compatibility record and a specimen-damage assessment. None of the designs below are past CONCEPT:
they are manufacturing concepts, not calibrated aperture or specimen-safety results.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .mmr import MMRLog

LADDER = ["CONCEPT", "RECEIVED", "MEASURED", "QUALIFIED", "IN_SERVICE", "RETIRED"]
FRAME = {"name": "baebugs universal insert frame", "insert_pocket_mm": (100.0, 100.0), "insert_thickness_mm": (0.3, 0.8),
         "retention": "printed clips + 4 x M3", "fits": "tower rail-arm trays (config/tower.yaml)"}

DESIGNS = {
    "C-HEX-2.5AF": {"concept": "C", "geometry": "hexagonal openings, 2.5 mm across flats", "catalog_id": "SS-HEX-2.5AF",
                    "route": "laser cut", "material": "316L stainless (304 cost comparator)", "thickness_mm": "0.3-0.8 (vendor-confirmed)",
                    "why": "distinct orientation and open-area alternative to round perforation"},
    "D-MESH-1.0": {"concept": "D", "geometry": "woven mesh, nominal 1.0 mm opening", "catalog_id": "SS-MESH-1.0",
                   "route": "purchased sheet, cut to insert", "material": "stainless woven wire", "thickness_mm": "per wire gauge",
                   "why": "replaceable sheet instead of fabricating each strand"},
    "D-MESH-2.0": {"concept": "D", "geometry": "woven mesh, nominal 2.0 mm opening", "catalog_id": "SS-MESH-2.0",
                   "route": "purchased sheet, cut to insert", "material": "stainless woven wire", "thickness_mm": "per wire gauge",
                   "why": "replaceable sheet instead of fabricating each strand"},
    "V-SQUARE-0-6": {"concept": "variable", "geometry": "two 6 mm square-hole plates, diagonal slide (0-6 mm square)",
                     "catalog_id": None, "route": "laser cut pair + lead screw", "material": "316L stainless",
                     "thickness_mm": "0.5", "why": "one sorter steps through size classes (variable_aperture.py)"},
}
REQUIRED_FOR_QUALIFIED = ["measured_aperture_mm", "deburred", "cleaning_compatibility", "damage_assessment"]


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def design_id(key):
    return H({"design": key, **DESIGNS[key]})


class Registry:
    def __init__(self, path="print/filters/inserts/registry_mmr.jsonl"):
        self.log = MMRLog(Path(path))

    def history(self, serial_id):
        return [r["record"] for r in self.log.records if r["record"].get("serial_id") == serial_id]

    def status(self, serial_id):
        h = self.history(serial_id)
        return h[-1]["status"] if h else None

    def register(self, design, serial, by):
        sid = H({"design_id": design_id(design), "serial": serial})
        if self.history(sid):
            raise ValueError(f"serial {serial} already registered")
        return self._add(sid, design, "CONCEPT", "registered", by, {"serial": serial})

    def advance(self, serial_id, to, by, evidence=None, nominal_tol_mm=0.1):
        cur = self.status(serial_id)
        if cur is None:
            raise KeyError(serial_id)
        if to != "RETIRED" and LADDER.index(to) != LADDER.index(cur) + 1:
            raise ValueError(f"{cur} -> {to} skips the ladder")
        ev = dict(evidence or {})
        if to == "QUALIFIED":
            merged = {}
            for r in self.history(serial_id):
                merged.update(r.get("evidence") or {})
            merged.update(ev)
            miss = [k for k in REQUIRED_FOR_QUALIFIED if k not in merged]
            if miss:
                raise ValueError(f"cannot qualify: missing {miss}")
            nom = merged.get("nominal_aperture_mm")
            if nom is not None and abs(merged["measured_aperture_mm"] - nom) > nominal_tol_mm:
                raise ValueError(f"measured {merged['measured_aperture_mm']} vs nominal {nom} outside tol")
        design = self.history(serial_id)[0]["design"]
        return self._add(serial_id, design, to, f"{cur}->{to}", by, ev)

    def log_event(self, serial_id, kind, by, evidence=None):
        """cleaning / use / inspection events that do not change status."""
        return self._add(serial_id, self.history(serial_id)[0]["design"], self.status(serial_id), kind, by, evidence or {})

    def _add(self, sid, design, status, event, by, evidence):
        rec = {"type": "insert", "serial_id": sid, "design": design, "design_id": design_id(design), "status": status,
               "event": event, "by": by, "evidence": evidence, "t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        self.log.append(rec)
        return rec
