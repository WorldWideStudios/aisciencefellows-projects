"""Bake PyMOL renders for Pareto-optimal capsids that don't yet have one.

Complements bake_capsid_structures.py — that script reads mutation strings from
the v1_release FASTA, but the extended-pool (synthetic) variants only live in
workbench/capsid_details.json. This pass:

  1. Reads workbench/capsid_pareto_data.json → picks all Pareto-optimal ids
  2. For each id without an existing workbench/esm3_pdbs/capsids/<id>/render.png
     reads its mutation_str from workbench/capsid_details.json
  3. Calls the same render_variant() PyMOL routine so the schema/appearance
     matches the original bake

Usage:
    ~/venv/bin/python -m aav_optimization.bake_missing_capsid_renders
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from aav_optimization.bake_capsid_structures import (
    OUT_DIR, fetch_alphafold_pdb, render_variant,
)

PARETO_JSON  = REPO / "workbench" / "capsid_pareto_data.json"
DETAILS_JSON = REPO / "workbench" / "capsid_details.json"


def main() -> None:
    print("=== Bake missing capsid renders ===\n")

    pareto = json.loads(PARETO_JSON.read_text())
    details = json.loads(DETAILS_JSON.read_text())

    front_ids = sorted({r["id"] for r in pareto["rows"] if r.get("front")})
    missing = [cid for cid in front_ids
               if not (OUT_DIR / cid / "render.png").exists()]

    print(f"Pareto-optimal capsids: {len(front_ids)}")
    print(f"Missing renders:        {len(missing)}\n")
    if not missing:
        print("Nothing to bake.")
        return

    pdb_path = fetch_alphafold_pdb()
    print()

    import pymol
    pymol.finish_launching(["pymol", "-cq"])
    from pymol import cmd
    print("PyMOL initialised\n", flush=True)

    for cid in missing:
        d = details.get(cid)
        if not d:
            print(f"  [{cid}]  no detail entry, skipping", flush=True)
            continue
        mut = d.get("mutation_str", "")
        print(f"  {cid}  [{d.get('class','?')}  H={d.get('hamming','?')}]  {mut[:60]}", flush=True)
        try:
            render_variant(cid, mut, pdb_path, cmd)
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)

    print(f"\nDone. PNGs in {OUT_DIR}/")


if __name__ == "__main__":
    main()
