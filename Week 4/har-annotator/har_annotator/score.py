"""Phase 3 — transparent, inspectable evidence score.

The score is a simple weighted sum of six normalized component scores, each in
[0, 1]. Every component is retained as its own ``score_<component>`` column so
the total is fully decomposable — there is no black box. Weights are explicit
module constants and can be overridden per run.

    total_score = sum(WEIGHTS[c] * score_<c> for c in COMPONENTS)

Components
----------
constraint     : mammalian constraint strength (phyloP mean), min-max scaled
acceleration   : real human-chimp substitution rate from the panTro5 ortholog
                 alignment (substitutions / aligned bp), min-max scaled
gene           : neurodev-gene link quality — DDG2P confidence tier, boosted if
                 the gene is assigned by PLAC-seq rather than nearest-TSS, and
                 decaying with HAR–TSS distance
disease        : neuropsychiatric GWAS overlap — significance (−log10 p) and
                 proximity to the lead SNP
brain          : active in the developing brain — ENCODE embryonic-cortex DNase
                 peak overlap (+ PLAC-seq ATAC support)  ["where"]
temporal       : target gene's prenatal expression concentrated in the mid-fetal
                 convergence window (~10-24 pcw), from BrainSpan  ["when"]
motif          : JASPAR TF-motif disruption — binding sites gained + lost
                 between the human and chimp alleles, min-max scaled
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COMPONENTS = ["constraint", "acceleration", "gene", "disease", "brain", "temporal", "motif"]

# Default weights — deliberately simple and legible, and they sum to 1.0.
# Constraint + disease + gene carry the most weight (they define the biological
# question); brain activity ("where") and temporal ("when") are the paired
# developmental-context axes; acceleration is a supporting proxy; motif reserved.
#
# NOTE: adding the temporal axis re-normalizes the six original weights, so this
# default will re-rank relative to the shipped v1 shortlist (that is the point —
# it introduces the developmental clock). To reproduce the original v1 ranking,
# run with the pre-temporal weights and temporal=0, e.g.:
#   --weights constraint=0.20,acceleration=0.10,gene=0.25,disease=0.25,brain=0.15,temporal=0,motif=0.05
WEIGHTS = {
    "constraint": 0.18,
    "acceleration": 0.07,
    "gene": 0.22,
    "disease": 0.22,
    "brain": 0.13,
    "temporal": 0.13,
    "motif": 0.05,
}

_CONF_SCORE = {"definitive": 1.0, "strong": 0.75, "moderate": 0.5,
               "limited": 0.3, "disputed": 0.1, "refuted": 0.0}


def _minmax(x: pd.Series) -> pd.Series:
    x = pd.to_numeric(x, errors="coerce")
    lo, hi = x.min(), x.max()
    if not np.isfinite(lo) or hi == lo:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return (x - lo) / (hi - lo)


def compute_scores(ev: pd.DataFrame, weights: dict | None = None,
                   gene_window: int = 1_000_000,
                   gwas_window: int = 25_000) -> pd.DataFrame:
    """Return ``ev`` with per-component score columns and a ``total_score``,
    sorted descending. All component columns are in [0, 1]."""
    w = {**WEIGHTS, **(weights or {})}
    df = ev.copy()

    # constraint: min-max scaled mean phyloP
    df["score_constraint"] = _minmax(df["phylop_mean"])

    # acceleration: REAL human-chimp substitution rate (substitutions per
    # aligned bp, from the panTro5 ortholog alignment), min-max scaled.
    # Falls back to the log-width proxy only if subst_rate is unavailable.
    if "subst_rate" in df and pd.to_numeric(df["subst_rate"], errors="coerce").notna().any():
        df["score_acceleration"] = _minmax(df["subst_rate"])
    else:
        df["score_acceleration"] = _minmax(np.log1p(df["width"]))

    # gene: confidence tier * distance-decay, +0.15 boost for PLAC-seq assignment
    conf = df["gene_confidence"].str.lower().map(_CONF_SCORE).fillna(0.3)
    dist_decay = 1.0 - (df["gene_distance"].clip(0, gene_window) / gene_window)
    plac_boost = np.where(df["gene_assignment_method"].eq("plac_linked"), 0.15, 0.0)
    df["score_gene"] = np.clip(conf * dist_decay + plac_boost, 0, 1)

    # disease: significance (−log10 p, capped at 50) * proximity decay
    neglogp = -np.log10(pd.to_numeric(df["gwas_pval"], errors="coerce").clip(lower=1e-300))
    sig = (neglogp.clip(0, 50) / 50.0)
    prox = 1.0 - (df["gwas_distance"].clip(0, gwas_window) / gwas_window)
    df["score_disease"] = np.clip(sig.fillna(0) * prox.fillna(0), 0, 1)

    # brain: DNase peak overlap (0.8) + PLAC-seq ATAC support (0.2)
    df["score_brain"] = (df["brain_dnase_overlap"].astype(float) * 0.8
                         + df["plac_atac"].fillna(False).astype(float) * 0.2)

    # temporal: fraction of the target gene's PRENATAL expression that falls in
    # the mid-fetal convergence window (BrainSpan). Missing gene -> 0.
    df["score_temporal"] = (pd.to_numeric(df.get("gene_midfetal_frac", 0.0),
                                          errors="coerce").fillna(0.0).clip(0, 1))

    # motif: REAL JASPAR motif disruption (TF binding sites gained + lost
    # between the human and chimp alleles), min-max scaled. If no motif
    # annotation is present the axis is 0 (its historical reserved state).
    if "motif_disruption" in df and pd.to_numeric(df["motif_disruption"], errors="coerce").notna().any():
        df["score_motif"] = _minmax(df["motif_disruption"])
    else:
        df["score_motif"] = pd.Series(0.0, index=df.index)

    contrib = []
    for c in COMPONENTS:
        col = f"contrib_{c}"
        df[col] = w[c] * df[f"score_{c}"]
        contrib.append(col)
    df["total_score"] = df[contrib].sum(axis=1)

    df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
    df.insert(0, "rank", np.arange(1, len(df) + 1))
    return df
