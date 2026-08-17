"""Read hypothesis_frontier + related tables → write workbench/frontier_data.json.

The frontier scatter viz reads this JSON. Kept lean: only the fields the
scatter + hover popover + right-panel detail need. Detail-load-on-click
can fetch richer chain data separately if we add a backend endpoint.

Run:
    ~/venv/bin/python -m prototype.ingest.hydrate_frontier_view
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DB  = REPO / "data" / "mechanism.sqlite"
OUT = REPO / "workbench" / "frontier_data.json"


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    raw = [dict(r) for r in conn.execute("""
        SELECT hypothesis_id,
               cohort, patient_id, patient_label,
               mechanism_family, mechanism_desc,
               variant_hgvsc, variant_hgvsp, variant_exon,
               pathway_id, pathway_name, pathway_dgc_coverage,
               cell_type, tissue,
               cell_dgc_completeness, cell_tissue_relevance,
               n_predicted, n_observed, n_intersect,
               coverage, depth, actionability,
               weighted_fit, therapeutic_reach, confidence, hypothesis_score,
               hypothesis_strength, aav_viability,
               max_predicted_severity, predicts_severe,
               is_pareto_within_patient, is_pareto_global,
               predicted_phenotypes, observed_phenotypes
        FROM hypothesis_frontier
        ORDER BY patient_label, mechanism_family, hypothesis_id
    """)]

    # ---- Deduplicate repeated strings across 16k rows -----------------
    # Repeated blobs: mechanism_desc (4 distinct), pathway (20), cell (20),
    # variant (10 patients), phenotype-sets. Dedup by lookup tables.
    mech_descs   = {}   # mech_id -> desc
    pathways     = {}   # pathway_id -> {name, dgc_coverage}
    cells        = {}   # cell_type -> {tissue, dgc_completeness, tissue_relevance}
    variants     = {}   # patient_label -> {hgvsc, hgvsp, exon}
    pheno_sets   = {}   # sorted tuple -> index
    pheno_order  = []
    for r in raw:
        mech_descs.setdefault(r["mechanism_family"], r["mechanism_desc"])
        if r["pathway_id"] not in pathways:
            pathways[r["pathway_id"]] = {
                "name": r["pathway_name"],
                "dgc": round(r["pathway_dgc_coverage"], 4),
            }
        if r["cell_type"] not in cells:
            cells[r["cell_type"]] = {
                "tissue": r["tissue"],
                "dgc": round(r["cell_dgc_completeness"], 4),
                "rel":  round(r["cell_tissue_relevance"], 3),
            }
        if r["patient_label"] not in variants:
            variants[r["patient_label"]] = {
                "hgvsc": r["variant_hgvsc"], "hgvsp": r["variant_hgvsp"],
                "exon":  r["variant_exon"],
            }

    def _pheno_idx(json_str: str) -> int:
        try:
            xs = tuple(sorted(json.loads(json_str) if json_str else []))
        except Exception:
            xs = ()
        if xs not in pheno_sets:
            pheno_sets[xs] = len(pheno_order)
            pheno_order.append(list(xs))
        return pheno_sets[xs]

    # ---- Slim per-row records (arrays > objects for size) --------------
    # Each row: [hid, patient_label, mech_id, pathway_id, cell_type,
    #            coverage, depth, actionability, n_pred, n_obs, n_int,
    #            pred_idx, obs_idx, is_pareto_within, is_pareto_global,
    #            weighted_fit, max_predicted_severity, predicts_severe]
    slim_rows = []
    for r in raw:
        pi = _pheno_idx(r["predicted_phenotypes"])
        oi = _pheno_idx(r["observed_phenotypes"])
        slim_rows.append([
            r["hypothesis_id"], r["patient_label"], r["mechanism_family"],
            r["pathway_id"], r["cell_type"],
            round(r["coverage"], 4), r["depth"], r["actionability"],
            r["n_predicted"], r["n_observed"], r["n_intersect"],
            pi, oi,
            r["is_pareto_within_patient"], r["is_pareto_global"],
            round(r["weighted_fit"] or 0.0, 6),
            r["max_predicted_severity"] or 0,
            r["predicts_severe"] or 0,
            round(r["therapeutic_reach"] or 0.0, 6),
            round(r["confidence"] or 0.0, 6),
            round(r["hypothesis_score"] or 0.0, 6),
            round(r["hypothesis_strength"] or 0.0, 6),
            round(r["aav_viability"] or 0.0, 6),
        ])

    patients = [{"cohort": c, "patient_id": pid, "label": lbl}
                for (c, pid, lbl) in conn.execute("""
        SELECT DISTINCT cohort, patient_id, patient_label
        FROM hypothesis_frontier ORDER BY patient_label
    """)]

    meta = {
        "n_rows":     len(slim_rows),
        "n_frontier_global": sum(r[14] for r in slim_rows),
        "n_frontier_within": sum(r[13] for r in slim_rows),
        "coverage_max": 1.0, "depth_max": 5, "actionability_max": 3,
        "mechanism_families": sorted(mech_descs.keys()),
        "mechanism_descs":    mech_descs,
        "pathways":           pathways,
        "cells":              cells,
        "variants":           variants,
        "phenotype_sets":     pheno_order,
        "patients":           patients,
        "row_fields": ["hid","patient","mech","pathway","cell",
                       "coverage","depth","actionability",
                       "n_pred","n_obs","n_int",
                       "pred_idx","obs_idx",
                       "is_frontier_p","is_frontier_g",
                       "weighted_fit","max_severity","predicts_severe",
                       "therapeutic_reach","confidence","hypothesis_score",
                       "hypothesis_strength","aav_viability"],
    }

    OUT.write_text(json.dumps({"meta": meta, "rows": slim_rows}, separators=(",", ":")))
    print(f"[frontier] {len(slim_rows)} rows · {meta['n_frontier_global']} global · "
          f"{meta['n_frontier_within']} within-patient frontier")
    print(f"[dedup]  {len(pathways)} pathways · {len(cells)} cells · "
          f"{len(variants)} variants · {len(pheno_order)} distinct phenotype-sets")
    print(f"[out] {OUT.relative_to(REPO)}  ({OUT.stat().st_size / 1024:.0f} KB)")
    conn.close()


if __name__ == "__main__":
    main()
