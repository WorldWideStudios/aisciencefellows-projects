"""Build the derived reference tables the funnel and evidence steps consume.

Each builder fetches its raw source through :mod:`har_annotator.download` (so
every pull is cached, hashed and logged to ``data/manifest.csv``) and writes a
tidy parquet. All are idempotent: if the parquet already exists and
``force=False`` it is loaded from cache instead of rebuilt.

    genes           refGene hg38 -> one row per gene symbol (chrom, strand, TSS)
    neurodev_genes  DDG2P developmental-disorder genes joined to genes, with
                    the highest DDG2P confidence tier per gene
    gwas_loci       EBI GWAS Catalog -> genome-wide-significant (p<5e-8)
                    neuropsychiatric/cognitive lead SNPs
    plac_links      Cui 2025 neuronal PLAC-seq -> HAR -> gene interaction links

Data-source substitution note: SFARI Gene was unreachable from the build
environment, so the neurodevelopmental gene set is DDG2P only. ``build_neurodev``
still unions any extra symbols passed via ``sfari_symbols=`` so a SFARI export
can be dropped in without code changes.
"""
from __future__ import annotations

import re
import numpy as np
import pandas as pd

from . import download as dl

_MAIN = {f"chr{i}" for i in range(1, 23)} | {"chrX", "chrY"}
_CONF_RANK = {"definitive": 5, "strong": 4, "moderate": 3,
              "limited": 2, "disputed": 1, "refuted": 0}
_NEURO_PAT = re.compile(
    r"schizophren|autis|bipolar|depress|neurotic|cognit|educational|intellig|"
    r"attention.deficit|adhd|alzheimer|neurodevelop|"
    r"intellectual disab|epileps|tourette|obsessive", re.I)

REFGENE_URL = "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/refGene.txt.gz"


def build_genes(force: bool = False) -> pd.DataFrame:
    """refGene hg38 -> one row per gene symbol with strand-aware TSS."""
    out = dl.DATA_DIR / "gene_coords_hg38.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    refg = dl.fetch(REFGENE_URL, "refgene_hg38", "refGene_hg38.txt.gz")
    cols = ["bin", "name", "chrom", "strand", "txStart", "txEnd", "cdsStart",
            "cdsEnd", "exonCount", "exonStarts", "exonEnds", "score", "name2",
            "cdsStartStat", "cdsEndStat", "exonFrames"]
    rg = pd.read_csv(refg, sep="\t", header=None, names=cols, low_memory=False)
    rg = rg[rg.chrom.isin(_MAIN)].copy()
    rg["tss"] = np.where(rg.strand == "+", rg.txStart, rg.txEnd)
    genes = (rg.groupby("name2")
             .agg(chrom=("chrom", "first"), strand=("strand", "first"),
                  gene_start=("txStart", "min"), gene_end=("txEnd", "max"),
                  tss=("tss", "median"))
             .reset_index().rename(columns={"name2": "symbol"}))
    genes["tss"] = genes["tss"].astype(int)
    genes.to_parquet(out)
    return genes


def build_neurodev(ddg2p_filename: str, sfari_symbols: set | None = None,
                   force: bool = False) -> pd.DataFrame:
    """DDG2P (+ optional SFARI symbols) joined to gene coordinates."""
    out = dl.DATA_DIR / "neurodev_genes.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    genes = build_genes(force=force)
    ddg2p = pd.read_csv(dl.DATA_DIR / ddg2p_filename, low_memory=False)
    ddg2p.columns = [c.strip() for c in ddg2p.columns]
    ddg2p["conf_num"] = ddg2p["confidence"].str.lower().map(_CONF_RANK).fillna(1)
    gene_conf = (ddg2p.groupby("gene symbol")
                 .agg(confidence=("confidence", lambda s: s.loc[ddg2p.loc[s.index, "conf_num"].idxmax()]),
                      conf_num=("conf_num", "max"),
                      n_disorders=("disease name", "nunique"),
                      diseases=("disease name", lambda s: "; ".join(sorted(set(s.dropna()))[:3])))
                 .reset_index().rename(columns={"gene symbol": "symbol"}))
    if sfari_symbols:
        extra = sorted(set(sfari_symbols) - set(gene_conf["symbol"]))
        if extra:
            add = pd.DataFrame({"symbol": extra, "confidence": "sfari",
                                "conf_num": 3, "n_disorders": 1, "diseases": "SFARI ASD gene"})
            gene_conf = pd.concat([gene_conf, add], ignore_index=True)
    neuro = gene_conf.merge(genes, on="symbol", how="left").dropna(subset=["chrom"]).copy()
    neuro["tss"] = neuro["tss"].astype(int)
    neuro[["gene_start", "gene_end"]] = neuro[["gene_start", "gene_end"]].astype(int)
    neuro.to_parquet(out)
    return neuro


def build_gwas_loci(gwas_zip_filename: str, pval_max: float = 5e-8,
                    force: bool = False) -> pd.DataFrame:
    """EBI GWAS Catalog -> genome-wide-significant neuropsychiatric lead SNPs."""
    out = dl.DATA_DIR / "gwas_neuropsych_loci.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    gwas = pd.read_csv(dl.DATA_DIR / gwas_zip_filename, sep="\t",
                       low_memory=False, compression="zip")
    mt = gwas["MAPPED_TRAIT"].fillna("") + " " + gwas["DISEASE/TRAIT"].fillna("")
    g = gwas[mt.str.contains(_NEURO_PAT)].copy()
    g["CHR_ID"] = g["CHR_ID"].astype(str).str.split(";").str[0].str.strip()
    g["CHR_POS"] = pd.to_numeric(g["CHR_POS"].astype(str).str.split(";").str[0], errors="coerce")
    g["pval"] = pd.to_numeric(g["P-VALUE"], errors="coerce")
    g = g.dropna(subset=["CHR_ID", "CHR_POS"])
    g = g[g["CHR_ID"].isin([str(i) for i in range(1, 23)] + ["X", "Y"])]
    g["chrom"] = "chr" + g["CHR_ID"]
    g["pos"] = g["CHR_POS"].astype(int)
    gsig = g[g["pval"] < pval_max].copy()
    loci = gsig[["chrom", "pos", "SNPS", "DISEASE/TRAIT", "MAPPED_TRAIT",
                 "pval", "PUBMEDID", "STUDY"]].rename(
        columns={"SNPS": "snp", "DISEASE/TRAIT": "trait", "MAPPED_TRAIT": "mapped_trait",
                 "PUBMEDID": "pubmed", "STUDY": "study"})
    loci = loci.drop_duplicates(subset=["chrom", "pos", "trait"])
    loci.to_parquet(out)
    return loci


def _har_ids(cell) -> list[str]:
    if pd.isna(cell):
        return []
    return re.findall(r"HAR_\d+", str(cell))


def build_plac_links(interaction_gene_table: pd.DataFrame,
                    force: bool = False) -> pd.DataFrame:
    """Cui 2025 neuronal PLAC-seq interaction-gene table -> HAR->gene links."""
    out = dl.DATA_DIR / "har_plac_gene_links.parquet"
    if out.exists() and not force:
        return pd.read_parquet(out)
    links = []
    ig = interaction_gene_table
    for _, r in ig.iterrows():
        gene = r["Gene name"]
        for h in _har_ids(r.get("HARs overlapped with promoter")):
            links.append((h, gene, "promoter", True))
        distal_atac = set(_har_ids(r.get("HARs in distal interacting regions with ATAC-seq peaks")))
        for h in _har_ids(r.get("HARs in distal interacting regions")):
            links.append((h, gene, "distal", h in distal_atac))
        for h in _har_ids(r.get("The nearest distal HAR")):
            links.append((h, gene, "nearest_distal", h in distal_atac))
    plac = pd.DataFrame(links, columns=["har_id", "plac_gene", "plac_type", "plac_atac"]).drop_duplicates()
    plac.to_parquet(out)
    return plac
