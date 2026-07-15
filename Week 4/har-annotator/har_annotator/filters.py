"""Phase 1 — the candidate funnel.

Sequentially narrows the full HAR set to constrained, neurodevelopment-adjacent,
disease-overlapping elements, logging the surviving count after every step.

All coordinates are hg38, 0-based half-open (BED convention). Overlap and
nearest-feature logic uses pyranges.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pyranges as pr

MAIN_CHROMS = [f"chr{i}" for i in range(1, 23)] + ["chrX", "chrY"]


def _pr(df: pd.DataFrame, extra: list[str] | None = None) -> pr.PyRanges:
    """Build a PyRanges from a df with chrom/start/end columns."""
    keep = ["Chromosome", "Start", "End"] + (extra or [])
    out = df.rename(columns={"chrom": "Chromosome", "start": "Start", "end": "End"})
    return pr.PyRanges(out[keep])


# ---------------------------------------------------------------------------
# Step A — mammalian constraint (Zoonomia 241-way phyloP, queried remotely)
# ---------------------------------------------------------------------------
PHYLOP_URL = (
    "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/cactus241way/cactus241way.phyloP.bw"
)


def annotate_phylop(hars: pd.DataFrame, bw=None) -> pd.DataFrame:
    """Add per-HAR phyloP mean and max from the remote 241-way bigWig.

    ``bw`` may be a pre-opened pyBigWig handle (avoids re-opening on reruns).
    """
    import pyBigWig

    close = False
    if bw is None:
        bw = pyBigWig.open(PHYLOP_URL)
        close = True
    chroms = bw.chroms()
    means, maxes = [], []
    for c, s, e in zip(hars["chrom"], hars["start"], hars["end"]):
        if c in chroms and e <= chroms[c]:
            means.append(bw.stats(c, int(s), int(e), type="mean")[0])
            maxes.append(bw.stats(c, int(s), int(e), type="max")[0])
        else:
            means.append(np.nan)
            maxes.append(np.nan)
    if close:
        bw.close()
    out = hars.copy()
    out["phylop_mean"] = pd.to_numeric(pd.Series(means), errors="coerce").values
    out["phylop_max"] = pd.to_numeric(pd.Series(maxes), errors="coerce").values
    return out


def filter_constrained(hars: pd.DataFrame, min_phylop_mean: float = 1.0) -> pd.DataFrame:
    """Keep HARs whose mean 241-way phyloP exceeds ``min_phylop_mean``.

    phyloP mean > 1 is a conventional threshold for significant mammalian
    conservation. HARs are conserved-then-accelerated, so most pass; this step
    removes HARs that are not robustly constrained across mammals.
    """
    return hars[hars["phylop_mean"] > min_phylop_mean].copy()


# ---------------------------------------------------------------------------
# Step B — proximity to a neurodevelopmental gene
# ---------------------------------------------------------------------------
def assign_nearest_gene(hars: pd.DataFrame, genes: pd.DataFrame,
                        window: int = 1_000_000) -> pd.DataFrame:
    """Assign each HAR to the nearest neurodev-gene TSS within ``window`` bp.

    Returns HARs with the assigned gene symbol, signed distance to TSS,
    gene confidence, and the assignment method ('nearest_tss'). HARs with no
    neurodev gene within the window are dropped.
    """
    g = genes.copy()
    g["Chromosome"] = g["chrom"]
    g["Start"] = g["tss"]
    g["End"] = g["tss"] + 1
    gpr = pr.PyRanges(g[["Chromosome", "Start", "End", "symbol", "confidence",
                         "conf_num", "n_disorders"]])
    hpr = _pr(hars.assign(_idx=np.arange(len(hars))), extra=["_idx", "har_id"])
    near = hpr.nearest(gpr, suffix="_gene")
    d = near.df
    # pyranges 'Distance' is unsigned bp gap (0 if overlapping)
    d = d[d["Distance"] <= window].copy()
    d = d.rename(columns={"symbol": "gene", "confidence": "gene_confidence",
                          "conf_num": "gene_conf_num", "n_disorders": "gene_n_disorders",
                          "Distance": "gene_distance"})
    d["gene_assignment_method"] = "nearest_tss"
    keep = ["_idx", "gene", "gene_distance", "gene_confidence", "gene_conf_num",
            "gene_n_disorders", "gene_assignment_method"]
    merged = hars.assign(_idx=np.arange(len(hars))).merge(d[keep], on="_idx", how="inner")
    return merged.drop(columns="_idx")


# ---------------------------------------------------------------------------
# Step C — overlap with a neuropsychiatric GWAS locus
# ---------------------------------------------------------------------------
def annotate_gwas(hars: pd.DataFrame, loci: pd.DataFrame,
                  window: int = 100_000) -> pd.DataFrame:
    """Annotate each HAR with the nearest genome-wide-significant neuropsychiatric
    GWAS association within ``window`` bp of the HAR (by lead-SNP position).

    Adds gwas_trait / gwas_snp / gwas_pval / gwas_pubmed / gwas_distance and a
    boolean ``has_gwas``. Does NOT drop rows — the disease overlap is scored, and
    the funnel's disease step is applied separately via ``keep_gwas``.
    """
    l = loci.copy()
    l["Chromosome"] = l["chrom"]
    l["Start"] = l["pos"]
    l["End"] = l["pos"] + 1
    lpr = pr.PyRanges(l[["Chromosome", "Start", "End", "snp", "trait",
                         "mapped_trait", "pval", "pubmed", "study"]])
    hpr = _pr(hars.assign(_idx=np.arange(len(hars))), extra=["_idx"])
    near = hpr.nearest(lpr, suffix="_gwas")
    d = near.df
    d = d.rename(columns={"snp": "gwas_snp", "trait": "gwas_trait",
                          "mapped_trait": "gwas_mapped_trait", "pval": "gwas_pval",
                          "pubmed": "gwas_pubmed", "study": "gwas_study",
                          "Distance": "gwas_distance"})
    # keep the single nearest locus per HAR
    d = d.sort_values("gwas_distance").drop_duplicates("_idx")
    keep = ["_idx", "gwas_snp", "gwas_trait", "gwas_mapped_trait", "gwas_pval",
            "gwas_pubmed", "gwas_study", "gwas_distance"]
    out = hars.assign(_idx=np.arange(len(hars))).merge(d[keep], on="_idx", how="left")
    out["has_gwas"] = out["gwas_distance"].notna() & (out["gwas_distance"] <= window)
    return out.drop(columns="_idx")


def keep_gwas(hars: pd.DataFrame) -> pd.DataFrame:
    return hars[hars["has_gwas"]].copy()
