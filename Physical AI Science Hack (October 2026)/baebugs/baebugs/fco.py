"""FCOs (custody objects) for baebugs, following the biobitworks FCO/FCG design:
one FCO per actor/source (a web page, a database record, a camera, a model, a
human), identified by the Merkle root of its content rather than a name tag.
FCOs hybridize at a Merkle break point into a new FCO whose parents are the
input roots, so any context the vision model used can be untangled later.

Each field is a leaf (hash of key + canonical value); the FCO id is the Merkle
root of its sorted leaves plus its kind and parents. Missing information is kept
explicit (status: 'unknown'), never silently dropped.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

from .explore import merkle_root


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _leaf(k, v) -> str:
    return _h(k + "=" + json.dumps(v, sort_keys=True, default=str))


@dataclass
class FCO:
    kind: str                      # e.g. essig_page, essig_label, gbif_record, measurement, context
    source: str                    # URL, device id, model id, person key hash
    fields: dict = field(default_factory=dict)
    parents: list[str] = field(default_factory=list)
    status: str = "observed"       # observed | inferred | unknown | blocked
    license: str | None = None
    t: float = field(default_factory=time.time)

    @property
    def leaves(self) -> list[str]:
        return [_leaf(k, self.fields[k]) for k in sorted(self.fields)]

    @property
    def id(self) -> str:
        head = _h(json.dumps({"kind": self.kind, "source": self.source,
                              "parents": sorted(self.parents)}, sort_keys=True))
        return merkle_root([head] + self.leaves)

    def to_dict(self):
        d = asdict(self); d["id"] = self.id; return d

    def prove(self, key: str) -> dict:
        """Inclusion material for one field (leaf + all leaves -> root)."""
        return {"key": key, "leaf": _leaf(key, self.fields[key]), "fco": self.id}


def hybridize(kind: str, *fcos: FCO, source="baebugs:hybridize", prefer=None) -> FCO:
    """Merge FCO fields at a break point. Later FCOs win on conflict unless
    `prefer` lists kinds in priority order; every conflict is recorded."""
    order = list(fcos)
    if prefer:
        rank = {k: i for i, k in enumerate(prefer)}
        order.sort(key=lambda f: rank.get(f.kind, -1))  # highest priority merged last, wins
    merged, provenance, conflicts = {}, {}, []
    for f in order:
        for k, v in f.fields.items():
            if v in (None, "", "unknown"):
                continue
            if k in merged and merged[k] != v:
                conflicts.append({"field": k, "kept": v, "from": f.id[:12],
                                  "replaced": merged[k], "was_from": provenance[k][:12]})
            merged[k], provenance[k] = v, f.id
    merged["_field_sources"] = provenance
    merged["_conflicts"] = conflicts
    return FCO(kind, source, merged, parents=[f.id for f in fcos],
               status="inferred" if len(fcos) > 1 else fcos[0].status)
