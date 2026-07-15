"""Phase 2 — per-element evidence spine.

For every candidate HAR, assemble a tidy record of RAW (pre-scoring) evidence
values across six axes:

  constraint      -- phyloP_mean, phylop_max (Zoonomia 241-way)
  acceleration    -- har_width (proxy for substitution burden; see phase0 note)
  gene_assignment -- nearest neurodev-gene symbol/distance/confidence, PLUS a
                     PLAC-seq linked neurodev gene where available (upgraded method)
  disease_overlap -- nearest neuropsychiatric GWAS trait/SNP/pval/distance/study
  brain_regulatory-- overlap with a developing-brain (embryonic cortex) DNase
                     peak, and PLAC-seq ATAC support
  (motif/literature placeholders are added downstream / in interpretation)

The schema is documented in ``EVIDENCE_SCHEMA``.
"""
from __future__ import annotations

import gzip

import numpy as np
import pandas as pd
import pyranges as pr

EVIDENCE_SCHEMA = {
    "har_id": "HAR identifier (Cui 2025)",
    "har_alt_id": "Cross-reference ID (HARsv2 / ZOOHAR)",
    "chrom/start/end/width": "hg38 coordinates and width (bp)",
    "phylop_mean": "mean Zoonomia 241-way phyloP over the HAR (mammalian constraint)",
    "phylop_max": "max Zoonomia 241-way phyloP over the HAR",
    "gene": "nearest neurodevelopmental-disorder gene (DDG2P) TSS",
    "gene_distance": "bp from HAR to nearest neurodev-gene TSS",
    "gene_confidence": "DDG2P confidence tier of the nearest gene",
    "gene_assignment_method": "'nearest_tss' or 'plac_linked' (upgraded)",
    "plac_gene": "neurodev gene physically linked to the HAR by neuronal PLAC-seq (Cui 2025), if any",
    "plac_type": "promoter / distal / nearest_distal interaction",
    "plac_atac": "whether the PLAC-seq-linked distal region carries a neuronal ATAC peak",
    "gwas_trait": "nearest genome-wide-sig neuropsychiatric GWAS trait",
    "gwas_snp": "lead SNP of that association",
    "gwas_pval": "association p-value",
    "gwas_distance": "bp from HAR to the GWAS lead SNP",
    "gwas_study": "GWAS Catalog study / PubMed",
    "brain_dnase_overlap": "HAR overlaps an ENCODE embryonic-brain DNase peak (bool)",
    "brain_dnase_peak": "peak id if overlapping",
}


def _peaks_pr(bed_gz) -> pr.PyRanges:
    df = pd.read_csv(bed_gz, sep="\t", comment=None, header=None, skiprows=1,
                     usecols=[0, 1, 2, 3], names=["Chromosome", "Start", "End", "peak_id"])
    return pr.PyRanges(df)


def annotate_brain_dnase(hars: pd.DataFrame, peaks_bed_gz) -> pd.DataFrame:
    """Flag HARs overlapping an ENCODE developing-brain DNase peak."""
    ppr = _peaks_pr(peaks_bed_gz)
    hpr = pr.PyRanges(hars.assign(_idx=np.arange(len(hars))).rename(
        columns={"chrom": "Chromosome", "start": "Start", "end": "End"})[
        ["Chromosome", "Start", "End", "_idx"]])
    ov = hpr.join(ppr, suffix="_pk").df
    hit = (ov.groupby("_idx")["peak_id"].first().rename("brain_dnase_peak")
           if len(ov) else pd.Series(dtype=object, name="brain_dnase_peak"))
    out = hars.assign(_idx=np.arange(len(hars))).merge(hit, on="_idx", how="left")
    out["brain_dnase_overlap"] = out["brain_dnase_peak"].notna()
    return out.drop(columns="_idx")


def add_plac_gene(hars: pd.DataFrame, plac: pd.DataFrame, neuro_symbols: set) -> pd.DataFrame:
    """Attach a PLAC-seq-linked NEURODEV gene per HAR, preferring promoter >
    distal+ATAC > distal > nearest_distal interactions. Upgrades the gene
    assignment method to 'plac_linked' when the PLAC-seq gene is a neurodev gene.
    """
    h = plac[plac["plac_gene"].isin(neuro_symbols)].copy()
    order = {"promoter": 0, "distal": 1, "nearest_distal": 2}
    h["_rank"] = h["plac_type"].map(order).fillna(3) - h["plac_atac"].astype(int) * 0.5
    h = h.sort_values("_rank").drop_duplicates("har_id")
    out = hars.merge(h[["har_id", "plac_gene", "plac_type", "plac_atac"]], on="har_id", how="left")
    # upgrade method where a neurodev PLAC-seq gene exists
    out["gene_assignment_method"] = np.where(
        out["plac_gene"].notna(), "plac_linked", out["gene_assignment_method"])
    return out


def assemble(candidates: pd.DataFrame, plac: pd.DataFrame, neuro: pd.DataFrame,
             peaks_bed_gz) -> pd.DataFrame:
    """Build the full evidence table from the Phase-1 candidate set."""
    neuro_symbols = set(neuro["symbol"])
    ev = add_plac_gene(candidates, plac, neuro_symbols)
    ev = annotate_brain_dnase(ev, peaks_bed_gz)
    cols = ["har_id", "har_alt_id", "chrom", "start", "end", "width",
            "phylop_mean", "phylop_max",
            "gene", "gene_distance", "gene_confidence", "gene_conf_num",
            "gene_n_disorders", "gene_assignment_method",
            "plac_gene", "plac_type", "plac_atac",
            "gwas_trait", "gwas_snp", "gwas_pval", "gwas_distance",
            "gwas_mapped_trait", "gwas_study", "gwas_pubmed",
            "brain_dnase_overlap", "brain_dnase_peak"]
    cols = [c for c in cols if c in ev.columns]
    return ev[cols].copy()
