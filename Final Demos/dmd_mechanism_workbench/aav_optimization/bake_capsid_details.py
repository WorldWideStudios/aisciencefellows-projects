"""Bake per-capsid sequence + evidence details for the therapeutics detail panel.

Reads:
  outputs/dmd_pareto_data.parquet          — evaluated capsids with sim scores
  ../JARVIS_for_bio/v1_release/data/sequences/capsid_variants.fasta
                                           — mutation strings per capsid

Writes:
  workbench/capsid_details.json  — {capsid_id: {mutations, insertion, subs,
                                    hamming, class, vp1_length, delta_pct,
                                    wt_ref}}

The therapeutics detail panel reads this file to render the 4 evidence blocks:
  1. Difference vs template PDB (mutation delta)
  2. NAb-escape evidence (novelty vs WT AAV2)
  3. Transduction evidence (insertion peptide match to ASSLNIA reference)
  4. Inflammatory-response evidence (hepatotox penalty terms)

Usage:
    ~/venv/bin/python -m aav_optimization.bake_capsid_details
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from Bio import SeqIO

REPO = Path(__file__).resolve().parent.parent
PARETO_PARQUET = REPO / "aav_optimization" / "outputs" / "dmd_pareto_data.parquet"
CAPSID_FASTA   = REPO.parent / "JARVIS_for_bio" / "v1_release" / "data" / "sequences" / "capsid_variants.fasta"
OUT_JSON       = REPO / "workbench" / "capsid_details.json"

# ASSLNIA is the Muller 2003 muscle-targeting reference peptide.
REFERENCE_PEPTIDE = "ASSLNIA"
# AAV2 VP1 canonical length
VP1_LENGTH = 735


def parse_mutations(mutation_str: str) -> tuple[str | None, list[dict]]:
    """Parse mutation string into (insertion_peptide_or_None, [{resi, wt, mut}])."""
    insertion = None
    subs: list[dict] = []
    for part in (mutation_str or "").split("+"):
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
                    subs.append({
                        "resi": int(m.group(2)),
                        "wt":   m.group(1),
                        "mut":  m.group(3),
                    })
    return insertion, subs


def peptide_similarity(peptide: str, ref: str) -> float:
    """Fraction of positions in `peptide` that match ref (aligned from position 0)."""
    if not peptide:
        return 0.0
    n = min(len(peptide), len(ref))
    if n == 0:
        return 0.0
    matches = sum(1 for a, b in zip(peptide[:n], ref[:n]) if a == b)
    return matches / n


def classify_vr_region(resi: int) -> str:
    """Map residue index → VR loop label."""
    if 263 <= resi <= 268: return "VR-I"
    if 449 <= resi <= 468: return "VR-IV"
    if 488 <= resi <= 505: return "VR-V"
    if 581 <= resi <= 593: return "VR-VIII"
    if 704 <= resi <= 714: return "VR-IX"
    return "backbone"


def main() -> None:
    print("=== Bake capsid_details.json ===\n")

    df = pd.read_parquet(PARETO_PARQUET)
    all_ids = set(df["capsid_id"].unique())
    print(f"Total unique capsids in pareto data: {len(all_ids)}")

    details: dict[str, dict] = {}
    matched = 0
    for rec in SeqIO.parse(CAPSID_FASTA, "fasta"):
        cid = rec.id.split("|")[0]
        if cid not in all_ids:
            continue
        parts = dict(p.split("=", 1) for p in rec.description.split("|")[1:] if "=" in p)
        mutation_str = parts.get("mutations", "")
        insertion, subs = parse_mutations(mutation_str)
        hamming = int(parts.get("hamming", 0) or 0)
        cls     = parts.get("class", "?")
        vp1_len = len(str(rec.seq))
        # Add peptide length for insertion contribution
        ins_len = len(insertion) if insertion else 0
        delta_pct = 100.0 * hamming / VP1_LENGTH if VP1_LENGTH else 0.0

        # Substitutions grouped by VR region
        sub_regions: dict[str, list[dict]] = {}
        for s in subs:
            r = classify_vr_region(s["resi"])
            sub_regions.setdefault(r, []).append(s)

        peptide_sim = peptide_similarity(insertion or "", REFERENCE_PEPTIDE)
        details[cid] = {
            "capsid_id": cid,
            "class":     cls,
            "hamming":   hamming,
            "delta_pct": round(delta_pct, 2),
            "vp1_length": vp1_len,
            "insertion": insertion,
            "insertion_length": ins_len,
            "insertion_site": "between VP1 residue 587 and 588 (VR-VIII surface loop)",
            "reference_peptide": REFERENCE_PEPTIDE,
            "peptide_similarity_to_ref": round(peptide_sim, 3),
            "substitutions": subs,
            "sub_regions":   sub_regions,
            "mutation_str":  mutation_str,
        }
        matched += 1

    print(f"Matched {matched}/{len(all_ids)} capsids with FASTA metadata")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(details, indent=2))
    print(f"\nWrote {len(details)} entries → {OUT_JSON}")


if __name__ == "__main__":
    main()
