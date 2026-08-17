"""Map Pareto-optimal AAV capsid variants to DMD hypotheses.

Reads:
  outputs/dmd_pareto_data.parquet  — all evaluated capsids with Pareto flags
  ../data/mechanism.sqlite         — hypothesis_frontier table

Writes:
  outputs/capsid_hypothesis_map.parquet  — (capsid_id, hypothesis_id, mapping_score, rank)
  ../data/mechanism.sqlite               — capsid_hypothesis_map table (upserted)

Mapping score = tissue_match × escape_bonus × payload_fit

  tissue_match  : 1.0 if capsid's tissue tropism profile matches hypothesis tissue; else 0.5
  escape_bonus  : 1 + 0.5 × (nab_escape − 0.40).clip(0)  — reward escape well above min
  payload_fit   : derived from mechanism_family (H01=0.10 — full DMD too large;
                  H02=0.90 — micro-dys; H03=0.60 — AAV-ASO; H04=0.75 — small isoforms)

Only Pareto-optimal, constraint-passing capsid variants are mapped.
Per hypothesis, the top 3 capsids by mapping_score are stored.
"""

import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dmd_config as config

MECHANISM_DB  = Path(__file__).resolve().parent.parent / "data" / "mechanism.sqlite"
PARETO_PARQUET = config.OUTPUTS_DIR / "dmd_pareto_data.parquet"
OUT_PARQUET    = config.OUTPUTS_DIR / "capsid_hypothesis_map.parquet"
TOP_N          = 3   # capsids to keep per hypothesis

# Tissue tropism profile: for each hypothesis tissue, which muscle_transduction
# range is "well-matched" (i.e. this capsid is optimized for this tissue)?
# DMD primarily affects skeletal muscle and heart; retina for Dp260 isoform;
# CNS/peripheral nerve for Dp140/Dp71.
TISSUE_TROPISM = {
    "skeletal_muscle":  "muscle",    # high muscle_transduction is ideal
    "smooth_muscle":    "muscle",
    "adipose":          "muscle",    # nearby muscle delivery; less critical
    "retina":           "retinal",   # AAV2 variant pool is retina-competent (from AMD work)
    "peripheral_nerve": "other",
    "kidney":           "other",
    "other":            "other",
}

# Payload fit: what fraction of the payload space is feasible for this mechanism?
# H01 = full-length DMD gene therapy (11 kb) — too large for any current AAV
# H02 = exon-skip / micro-dystrophin (3.7 kb) — fits AAV4.7kb limit
# H03 = ASO / CRISPR delivered by AAV (smaller payload)
# H04 = distal short isoforms (Dp71/Dp140 driven by smaller promoters)
PAYLOAD_FIT = {"01": 0.10, "02": 0.90, "03": 0.60, "04": 0.75}


def tissue_match_score(capsid_tissue: str, hyp_tissue: str) -> float:
    """1.0 if capsid tropism aligns with hypothesis tissue; 0.5 otherwise."""
    cap_profile = TISSUE_TROPISM.get(hyp_tissue, "other")
    if capsid_tissue == cap_profile:
        return 1.0
    return 0.5


def assign_capsid_tropism(row: pd.Series) -> str:
    """Classify a capsid as 'muscle' or 'retinal' based on its sim outputs.

    - muscle_transduction > 0.35 → muscle-tropic
    - muscle_transduction <= 0.35 → retinal-tropic (these are AAV2 variants that
      retain retinal tropism from the AMD pool; usable for Dp260/retinal hypotheses)
    """
    if row["muscle_transduction"] > 0.35:
        return "muscle"
    return "retinal"


def compute_mapping_scores(
    capsids: pd.DataFrame,
    hypotheses: pd.DataFrame,
) -> pd.DataFrame:
    """Cross-join capsids × hypotheses, compute mapping score, keep top-N per hypothesis."""
    rows = []
    for _, hyp in hypotheses.iterrows():
        hyp_tissue  = hyp["tissue"]
        mech_family = str(hyp["mechanism_family"])
        pfit        = PAYLOAD_FIT.get(mech_family, 0.30)

        for _, cap in capsids.iterrows():
            cap_tropism = assign_capsid_tropism(cap)
            tmatch      = tissue_match_score(cap_tropism, hyp_tissue)
            escape_bonus = 1.0 + 0.5 * max(0.0, cap["nab_escape"] - 0.40)
            mapping_score = tmatch * escape_bonus * pfit * cap["muscle_transduction"]

            rows.append({
                "capsid_id":     cap["capsid_id"],
                "hypothesis_id": hyp["hypothesis_id"],
                "patient_id":    hyp.get("patient_id", None),
                "tissue":        hyp_tissue,
                "mechanism_family": mech_family,
                "capsid_tropism":   cap_tropism,
                "muscle_transduction": cap["muscle_transduction"],
                "nab_escape":     cap["nab_escape"],
                "hepatotoxicity_score": cap["hepatotoxicity_score"],
                "tissue_match":   tmatch,
                "payload_fit":    pfit,
                "escape_bonus":   round(escape_bonus, 4),
                "mapping_score":  round(mapping_score, 6),
                "selection_strategy": cap.get("selection_strategy", "unknown"),
                "cycle":          cap.get("cycle", -1),
                "is_on_pareto_frontier": cap.get("is_on_pareto_frontier", False),
            })

    df = pd.DataFrame(rows)
    # Rank within each hypothesis by mapping_score DESC; keep top-N
    df["rank"] = df.groupby("hypothesis_id")["mapping_score"] \
                   .rank(method="first", ascending=False).astype(int)
    df = df[df["rank"] <= TOP_N].reset_index(drop=True)
    return df.sort_values(["hypothesis_id", "rank"])


def write_to_sqlite(map_df: pd.DataFrame, db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE IF EXISTS capsid_hypothesis_map")
    conn.execute("""
        CREATE TABLE capsid_hypothesis_map (
            capsid_id            TEXT NOT NULL,
            hypothesis_id        TEXT NOT NULL,
            patient_id           TEXT,
            tissue               TEXT,
            mechanism_family     TEXT,
            capsid_tropism       TEXT,
            muscle_transduction  REAL,
            nab_escape           REAL,
            hepatotoxicity_score REAL,
            tissue_match         REAL,
            payload_fit          REAL,
            escape_bonus         REAL,
            mapping_score        REAL,
            selection_strategy   TEXT,
            cycle                INTEGER,
            is_on_pareto_frontier INTEGER,
            rank                 INTEGER,
            PRIMARY KEY (mechanism_family, tissue, rank)
        )
    """)
    map_df.to_sql("capsid_hypothesis_map", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()
    print(f"  Wrote {len(map_df)} rows to capsid_hypothesis_map in {db_path}")


def main() -> None:
    print("=== DMD Capsid → Hypothesis Mapping ===\n")

    # Load Pareto-optimal capsids (constraint-passing)
    all_caps = pd.read_parquet(PARETO_PARQUET)
    capsids  = all_caps[
        (all_caps["is_on_pareto_frontier"] == True) &
        (all_caps["meets_constraint"] == True)
    ].copy()
    print(f"Pareto-optimal constraint-passing capsids: {len(capsids)}")

    if len(capsids) == 0:
        # Fall back to top-20 by muscle_transduction from constraint-passing set
        capsids = all_caps[all_caps["meets_constraint"] == True] \
                    .nlargest(20, "muscle_transduction").copy()
        print(f"  (no Pareto front found — using top-20 by muscle_transduction)")

    # Load unique (mechanism_family, tissue) archetypes from the full frontier.
    # We score capsids against archetypes (not per-patient rows) so the mapping
    # is agnostic to patient-specific lab adjustments.
    conn = sqlite3.connect(MECHANISM_DB)
    hypotheses = pd.read_sql("""
        SELECT mechanism_family, tissue,
               GROUP_CONCAT(DISTINCT hypothesis_id) AS example_hypothesis_ids,
               COUNT(DISTINCT hypothesis_id) AS n_hypotheses
        FROM hypothesis_frontier
        GROUP BY mechanism_family, tissue
    """, conn)
    # Give each archetype a synthetic id
    hypotheses["hypothesis_id"] = (
        "arch_" + hypotheses["mechanism_family"] + "_" + hypotheses["tissue"].str.replace(" ", "_")
    )
    hypotheses["patient_id"] = None
    conn.close()
    print(f"Unique (mechanism, tissue) archetypes: {len(hypotheses)}")

    # Compute mapping scores
    print("Computing capsid × hypothesis mapping scores...")
    map_df = compute_mapping_scores(capsids, hypotheses)
    print(f"  mapped {len(map_df)} (hypothesis, capsid) pairs (top-{TOP_N} per hypothesis)")

    # Save outputs
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    map_df.to_parquet(OUT_PARQUET, index=False)
    print(f"  saved {OUT_PARQUET}")

    write_to_sqlite(map_df, MECHANISM_DB)

    # Best capsid per archetype (rank=1 rows)
    best = map_df[map_df["rank"] == 1].sort_values("mapping_score", ascending=False)
    print("\nBest capsid per (mechanism, tissue) archetype:")
    print(best[["mechanism_family", "tissue", "capsid_id", "mapping_score",
                "muscle_transduction", "nab_escape", "hepatotoxicity_score",
                "capsid_tropism"]].to_string(index=False))


if __name__ == "__main__":
    main()
