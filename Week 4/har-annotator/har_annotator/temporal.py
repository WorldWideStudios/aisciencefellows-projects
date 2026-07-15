"""Temporal axis — *when* during gestation does a HAR's target gene act?

Adds a developmental-timing dimension to the annotator. For each candidate HAR
we look up its assigned neurodevelopmental target gene in the **BrainSpan**
developmental transcriptome and ask *when* that gene peaks across gestation, and
how concentrated its prenatal expression is in the **mid-fetal convergence
window** (~10–24 post-conception weeks) — the window where human-specific
regulation and neuropsychiatric-risk-gene expression are thought to coincide.

This turns the static three-way intersection (conserved x brain gene x disease)
into a *timed* one: it up-weights HARs whose target gene fires in the same
developmental moment where disease risk converges.

New evidence fields
    temporal_gene        gene whose trajectory was used (plac_gene if present, else nearest `gene`)
    gene_peak_pcw        post-conception week of peak *prenatal* expression of that gene
    gene_midfetal_frac   fraction of prenatal expression inside the mid-fetal window  [0, 1]
    gene_in_midfetal     whether the prenatal peak falls inside the window (bool)

New score component
    temporal  =  gene_midfetal_frac         (already in [0, 1]; missing -> 0)

Source
    BrainSpan "RNA-Seq Gencode v10 summarized to genes" (Allen Institute), a zip
    of expression_matrix.csv (genes x samples, RPKM), columns_metadata.csv
    (per-sample donor / age / structure) and rows_metadata.csv (per-row gene
    symbol). Default download:
    https://www.brainspan.org/api/v2/well_known_file_download/267666525
    (If that well-known-file id changes, pass a local zip via ``brainspan_zip=``.)
"""
from __future__ import annotations

import io
import re
import zipfile

import numpy as np
import pandas as pd

from . import download as dl

BRAINSPAN_URL = "https://www.brainspan.org/api/v2/well_known_file_download/267666525"

# Mid-fetal convergence window, in post-conception weeks (inclusive).
# ~10-24 pcw brackets the early/mid-fetal period where neuropsychiatric risk
# genes co-express (Willsey/State-style convergence). Parameterized everywhere.
MIDFETAL_PCW = (10, 24)

_PCW_RE = re.compile(r"^\s*([\d.]+)\s*pcw\s*$", re.I)


def _parse_age_to_pcw(age) -> float:
    """'8 pcw' -> 8.0 ; postnatal ('4 mos', '1 yrs') -> NaN (prenatal only)."""
    m = _PCW_RE.match(str(age))
    return float(m.group(1)) if m else np.nan


def _trajectories_from_frames(expr: pd.DataFrame, cols_meta: pd.DataFrame,
                              rows_meta: pd.DataFrame,
                              midfetal=MIDFETAL_PCW) -> pd.DataFrame:
    """Pure, network-free core (unit-tested). ``expr`` is genes x samples with
    columns aligned to ``cols_meta`` rows and index aligned to ``rows_meta``.

    Returns one row per gene symbol: peak prenatal pcw, mid-fetal fraction, and
    an in-window flag. Duplicate symbols collapse to the highest-expressed copy.
    """
    lo, hi = midfetal
    pcw = cols_meta["age"].map(_parse_age_to_pcw).to_numpy(dtype=float)
    prenatal = ~np.isnan(pcw)
    if not prenatal.any():
        raise ValueError("no prenatal (pcw) samples found in columns_metadata")

    E = np.asarray(expr, dtype=float)[:, prenatal]      # genes x prenatal-samples
    pcw_p = pcw[prenatal]
    bins = np.unique(pcw_p)                              # sorted pcw values present

    # mean expression per gene at each pcw bin (average across brain structures)
    binned = np.column_stack([E[:, pcw_p == b].mean(axis=1) for b in bins])  # genes x bins

    total = binned.sum(axis=1)
    in_win = (bins >= lo) & (bins <= hi)
    win_sum = binned[:, in_win].sum(axis=1)
    peak_pcw = bins[binned.argmax(axis=1)]

    out = pd.DataFrame({
        "symbol": rows_meta["gene_symbol"].to_numpy(),
        "gene_peak_pcw": peak_pcw,
        "gene_midfetal_frac": np.where(total > 0, win_sum / total, 0.0),
        "gene_in_midfetal": (peak_pcw >= lo) & (peak_pcw <= hi),
        "_tot": total,
    })
    out = (out.sort_values("_tot", ascending=False)
              .drop_duplicates("symbol")
              .drop(columns="_tot")
              .reset_index(drop=True))
    return out


def build_brainspan_trajectories(midfetal=MIDFETAL_PCW, brainspan_zip: str | None = None,
                                 force: bool = False) -> pd.DataFrame:
    """Fetch BrainSpan (cached + hashed via download.fetch) and build per-gene
    developmental-timing trajectories. Idempotent: cached to a parquet."""
    out = dl.DATA_DIR / "brainspan_trajectories.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)

    zpath = (brainspan_zip if brainspan_zip
             else dl.fetch(BRAINSPAN_URL, "brainspan_devtx", "brainspan_rnaseq_genes.zip"))
    with zipfile.ZipFile(zpath) as z:
        names = {n.split("/")[-1]: n for n in z.namelist()}
        expr = pd.read_csv(io.BytesIO(z.read(names["expression_matrix.csv"])), header=None)
        cols_meta = pd.read_csv(io.BytesIO(z.read(names["columns_metadata.csv"])))
        rows_meta = pd.read_csv(io.BytesIO(z.read(names["rows_metadata.csv"])))

    # expression_matrix.csv has a leading 1-based row-index column; drop it so
    # columns align 1:1 with columns_metadata rows.
    expr = expr.iloc[:, 1:]
    if expr.shape[1] != len(cols_meta):
        raise ValueError(f"expr cols ({expr.shape[1]}) != columns_metadata rows ({len(cols_meta)})")
    if expr.shape[0] != len(rows_meta):
        raise ValueError(f"expr rows ({expr.shape[0]}) != rows_metadata rows ({len(rows_meta)})")

    traj = _trajectories_from_frames(expr, cols_meta, rows_meta, midfetal=midfetal)
    traj.to_parquet(out)
    return traj


def annotate_temporal(ev: pd.DataFrame, traj: pd.DataFrame) -> pd.DataFrame:
    """Attach temporal evidence to the per-HAR table. Uses the PLAC-seq-linked
    gene when present (higher-confidence target), else the nearest neurodev gene.
    Genes absent from BrainSpan get frac=0 / in_midfetal=False (score 0)."""
    ev = ev.copy()
    plac = ev["plac_gene"] if "plac_gene" in ev else pd.Series(index=ev.index, dtype=object)
    ev["temporal_gene"] = plac.where(plac.notna(), ev["gene"])
    m = traj.set_index("symbol")
    ev["gene_peak_pcw"] = ev["temporal_gene"].map(m["gene_peak_pcw"])
    ev["gene_midfetal_frac"] = ev["temporal_gene"].map(m["gene_midfetal_frac"]).fillna(0.0)
    ev["gene_in_midfetal"] = ev["temporal_gene"].map(m["gene_in_midfetal"]).fillna(False)
    return ev


# Evidence-schema fragment to merge into EVIDENCE_SCHEMA / har_evidence_schema.json
TEMPORAL_SCHEMA = {
    "temporal_gene": "target gene used for timing (plac_gene if linked, else nearest neurodev gene)",
    "gene_peak_pcw": "post-conception week of peak PRENATAL expression of the target gene (BrainSpan)",
    "gene_midfetal_frac": "fraction of the target gene's prenatal expression inside the mid-fetal window [0,1]",
    "gene_in_midfetal": "whether the prenatal expression peak falls inside the mid-fetal window (bool)",
}
