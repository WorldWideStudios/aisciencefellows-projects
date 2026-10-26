"""Claude vs BYO: compare two builds of the same graph and find the Merkle break points.

Both sides produce the same kind of pack (`python -m baebugs.mvp` on their own tree, or an FCO of the files
they have). Comparison goes top-down, so a reader sees at once where two builds part ways:

  root      equal -> the builds are identical; stop
  module    equal roots are skipped; unequal modules are break points
  leaf      inside a broken module: MATCH / DIFFERS / ONLY_A / ONLY_B per path

Bytes are the identity for code, prints and labware. Trained weights almost never match byte for byte
(non-deterministic training), so for them the comparison is by behaviour, not bytes; see baebugs.address.

  python -m baebugs.compare packA.json packB.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _modules(pack):
    if "modules" in pack:
        return {m: d["root"] for m, d in pack["modules"].items()}
    return {}


def compare(a, b, label_a="A", label_b="B"):
    out = {"type": "baebugs-compare", label_a: a.get("root"), label_b: b.get("root"),
           "identical": bool(a.get("root")) and a.get("root") == b.get("root"), "break_points": [], "modules": {}}
    if out["identical"]:
        return out
    ma, mb = _modules(a), _modules(b)
    la = {x["path"]: x for x in a.get("leaves", [])}
    lb = {x["path"]: x for x in b.get("leaves", [])}
    mod_of = {p: x.get("module", "?") for p, x in {**lb, **la}.items()}
    mods = sorted(set(ma) | set(mb) | set(mod_of.values()))
    for m in mods:
        if ma.get(m) and ma.get(m) == mb.get(m):
            out["modules"][m] = {"verdict": "SAME", "root": ma[m]}
            continue
        paths = sorted(p for p, mm in mod_of.items() if mm == m)
        rows = {"MATCH": 0, "DIFFERS": [], f"ONLY_{label_a}": [], f"ONLY_{label_b}": []}
        for p in paths:
            x, y = la.get(p), lb.get(p)
            if x and y:
                if x["sha256"] == y["sha256"]:
                    rows["MATCH"] += 1
                else:
                    rows["DIFFERS"].append(p)
            elif x:
                rows[f"ONLY_{label_a}"].append(p)
            else:
                rows[f"ONLY_{label_b}"].append(p)
        changed = rows["DIFFERS"] or rows[f"ONLY_{label_a}"] or rows[f"ONLY_{label_b}"]
        out["modules"][m] = {"verdict": "BREAK" if changed else "SAME_LEAVES", "root_" + label_a: ma.get(m),
                             "root_" + label_b: mb.get(m), **rows}
        if changed:
            out["break_points"].append(m)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a, b = (json.loads(Path(p).read_text()) for p in argv[:2])
    print(json.dumps(compare(a, b, "claude", "byo"), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
