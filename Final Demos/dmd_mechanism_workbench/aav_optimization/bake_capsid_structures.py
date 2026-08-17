"""Bake PyMOL renders of Pareto-optimal AAV capsid variants.

For each Pareto-optimal variant:
  1. Load AlphaFold AAV2 VP1 structure (UniProt P03135, cached locally)
  2. Color all five VR loops distinctly; backbone in lightblue
  3. Mark substituted residues as spheres with mutation labels
  4. Mark insertion site (residue 587) with a magenta sphere
  5. Render to workbench/esm3_pdbs/capsids/<capsid_id>/render.png

The AlphaFold PDB is also saved to workbench/esm3_pdbs/capsids/aav2_wt.pdb
so the 3Dmol interactive viewer can load it client-side.

Usage:
    ~/venv/bin/python -m aav_optimization.bake_capsid_structures
"""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd
from Bio import SeqIO

REPO = Path(__file__).resolve().parent.parent
PARETO_PARQUET = REPO / "aav_optimization" / "outputs" / "dmd_pareto_data.parquet"
CAPSID_FASTA   = REPO.parent / "JARVIS_for_bio" / "v1_release" / "data" / "sequences" / "capsid_variants.fasta"
OUT_DIR        = REPO / "workbench" / "esm3_pdbs" / "capsids"
# AAV2 VP3 crystal structure (2.6 Å, RCSB 2QA0, chain A, residues 220-738).
# Covers VP1 numbering for all five VR loops (263-268, 449-468, 488-505, 581-593, 704-714).
# Better than AlphaFold for this use case — experimentally solved.
WT_PDB_URL   = "https://files.rcsb.org/download/2QA0.pdb"
AF_PDB_LOCAL = OUT_DIR / "aav2_wt.pdb"

# VR loops: (start_resi, end_resi, pymol_color, hex_for_legend)
VR_LOOPS = {
    "VR-I":    (263, 268, "palegreen",   "#90ee90"),
    "VR-IV":   (449, 468, "yellow",      "#ffd700"),
    "VR-V":    (488, 505, "orange",      "#ff8c00"),
    "VR-VIII": (581, 593, "magenta",     "#cc44cc"),   # insertion site
    "VR-IX":   (704, 714, "violet",      "#8a2be2"),
}


# ── helpers ────────────────────────────────────────────────────────────────

def fetch_alphafold_pdb() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if AF_PDB_LOCAL.exists() and AF_PDB_LOCAL.stat().st_size > 10_000:
        print(f"  AAV2 VP3 PDB cached: {AF_PDB_LOCAL}")
        return AF_PDB_LOCAL
    print(f"  Fetching AAV2 VP3 crystal structure (RCSB 2QA0) …", flush=True)
    with urllib.request.urlopen(WT_PDB_URL, timeout=60) as r:
        data = r.read()
    AF_PDB_LOCAL.write_bytes(data)
    print(f"  Saved {len(data)//1024} KB → {AF_PDB_LOCAL}")
    return AF_PDB_LOCAL


def parse_mutations(mutation_str: str) -> tuple[str | None, list[tuple[int, str, str]]]:
    """Parse FASTA mutation string.

    Returns (insertion_peptide_or_None, [(resi, wt_aa, mut_aa), ...]).
    Example: 'ins587_588:ALSETRP+S452K,R459F'
    """
    insertion = None
    subs: list[tuple[int, str, str]] = []
    for part in mutation_str.split("+"):
        part = part.strip()
        if part.startswith("ins"):
            m = re.search(r":([A-Z]+)$", part)
            if m:
                insertion = m.group(1)
        else:
            for sub in part.split(","):
                sub = sub.strip()
                m = re.match(r"([A-Z])(\d+)([A-Z])", sub)
                if m:
                    subs.append((int(m.group(2)), m.group(1), m.group(3)))
    return insertion, subs


def render_variant(capsid_id: str, mutation_str: str, pdb_path: Path, cmd) -> Path:
    """PyMOL headless render. Returns path to saved PNG. cmd is the live PyMOL cmd module."""
    out_dir = OUT_DIR / capsid_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_png = out_dir / "render.png"

    if out_png.exists() and out_png.stat().st_size > 1000:
        print(f"    [{capsid_id}] PNG exists, skipping", flush=True)
        return out_png

    insertion, subs = parse_mutations(mutation_str)

    cmd.reinitialize()
    cmd.load(str(pdb_path), "capsid")
    cmd.hide("everything", "capsid")
    cmd.show("cartoon", "capsid")
    cmd.color("lightblue", "capsid")

    # Color VR loops
    for loop_name, (start, end, color, _) in VR_LOOPS.items():
        sel = f"capsid and resi {start}-{end}"
        cmd.color(color, sel)
        cmd.show("sticks", sel)

    # Mark substituted residues
    for resi, wt_aa, mut_aa in subs:
        sel = f"capsid and resi {resi} and name CA"
        cmd.show("spheres", sel)
        cmd.color("firebrick", sel)
        cmd.set("sphere_scale", 1.8, sel)
        cmd.label(sel, f'"{wt_aa}{resi}{mut_aa}"')

    # Mark insertion site (between 587 and 588)
    ins_sel = "capsid and resi 587 and name CA"
    cmd.show("spheres", ins_sel)
    cmd.color("hotpink", ins_sel)
    cmd.set("sphere_scale", 2.5, ins_sel)
    if insertion:
        cmd.label(ins_sel, f'"ins:{insertion}"')

    cmd.set("label_size", 14)
    cmd.set("label_color", "black")
    cmd.set("label_font_id", 7)
    cmd.bg_color("white")
    cmd.set("ray_opaque_background", 1)
    cmd.set("ray_shadows", 0)
    cmd.orient("capsid")
    cmd.zoom("capsid", buffer=4)
    cmd.png(str(out_png), width=600, height=450, dpi=100, ray=0)
    cmd.delete("all")

    print(f"    [{capsid_id}] → {out_png}", flush=True)
    return out_png


# ── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=== Bake AAV capsid PyMOL renders ===\n")

    # Load Pareto capsids
    df = pd.read_parquet(PARETO_PARQUET)
    pareto_ids = set(df[df["is_on_pareto_frontier"] == True]["capsid_id"].unique())
    print(f"Pareto-optimal capsids: {len(pareto_ids)}")

    # Parse FASTA metadata
    meta: dict[str, dict] = {}
    for rec in SeqIO.parse(CAPSID_FASTA, "fasta"):
        cid = rec.id.split("|")[0]
        if cid in pareto_ids:
            parts = dict(p.split("=", 1) for p in rec.description.split("|")[1:] if "=" in p)
            meta[cid] = parts

    print(f"Found FASTA metadata for {len(meta)} Pareto variants\n")

    # Fetch AAV2 VP3 crystal structure
    pdb_path = fetch_alphafold_pdb()
    print()

    # Init PyMOL once for the whole session
    import pymol
    pymol.finish_launching(["pymol", "-cq"])
    from pymol import cmd
    print("PyMOL initialised\n", flush=True)

    # Render each variant
    for cid, parts in sorted(meta.items()):
        mutation_str = parts.get("mutations", "")
        cls          = parts.get("class", "?")
        hamming      = parts.get("hamming", "?")
        print(f"  {cid}  [{cls}  H={hamming}]  {mutation_str[:60]}", flush=True)
        try:
            render_variant(cid, mutation_str, pdb_path, cmd)
        except Exception as e:
            print(f"    ERROR: {e}", flush=True)

    print(f"\nDone. PNGs in {OUT_DIR}/")
    print("AlphaFold PDB for 3Dmol viewer: workbench/esm3_pdbs/capsids/aav2_wt.pdb")


if __name__ == "__main__":
    main()
