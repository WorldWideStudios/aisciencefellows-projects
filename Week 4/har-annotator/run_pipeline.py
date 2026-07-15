#!/usr/bin/env python
"""HAR annotator — end-to-end driver.

Replays the whole pipeline from source data to the ranked shortlist, with every
window and threshold exposed as a command-line parameter. All data pulls are
cached and hashed under ``data/`` (see ``data/manifest.csv``); reruns reuse the
cache unless ``--force-download`` is given.

    python run_pipeline.py                       # defaults (reproduces the shipped shortlist)
    python run_pipeline.py --gwas-window 50000   # wider disease window
    python run_pipeline.py --min-phylop 1.5 --gene-window 500000
    python run_pipeline.py --weights gene=0.35,disease=0.30

Stages
    0  download + build reference tables (genes, neurodev, GWAS loci, PLAC-seq)
    1  funnel: constraint -> neurodev-gene proximity -> GWAS overlap
    2  per-element evidence spine
    3  transparent additive score + ranking
Outputs (to --outdir, default '.'):
    funnel_counts.csv, candidate_hars.parquet, har_evidence.parquet,
    har_shortlist_ranked.csv/.parquet
"""
from __future__ import annotations

import argparse
import sys
import pathlib

import pandas as pd


def parse_weights(s: str | None) -> dict | None:
    if not s:
        return None
    out = {}
    for kv in s.split(","):
        k, v = kv.split("=")
        out[k.strip()] = float(v)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min-phylop", type=float, default=1.0,
                    help="Step A: minimum mean 241-way phyloP (default 1.0)")
    ap.add_argument("--gene-window", type=int, default=1_000_000,
                    help="Step B: max HAR-TSS distance to a neurodev gene, bp (default 1e6)")
    ap.add_argument("--gwas-window", type=int, default=25_000,
                    help="Step C: max HAR-lead-SNP distance, bp (default 25000)")
    ap.add_argument("--gwas-pval", type=float, default=5e-8,
                    help="GWAS genome-wide significance cutoff (default 5e-8)")
    ap.add_argument("--weights", type=str, default=None,
                    help="Override score weights, e.g. 'gene=0.3,disease=0.3'")
    ap.add_argument("--ddg2p", type=str, default="DDG2P_2026-06-28.csv.gz",
                    help="DDG2P csv.gz filename under data/ (already fetched)")
    ap.add_argument("--gwas-zip", type=str,
                    default="gwas-catalog-associations_ontology-annotated-full.zip",
                    help="GWAS Catalog zip filename under data/ (already fetched)")
    ap.add_argument("--peaks", type=str,
                    default="ENCFF660HML_brain_embryo105d_DNase_peaks_hg38.bed.gz",
                    help="Developing-brain DNase peaks bed.gz filename under data/")
    ap.add_argument("--midfetal-window", type=str, default="10,24",
                    help="Mid-fetal convergence window in post-conception weeks, "
                         "'lo,hi' (default 10,24). Drives the temporal axis.")
    ap.add_argument("--brainspan", type=str, default=None,
                    help="Optional local BrainSpan zip path (else fetched from Allen).")
    ap.add_argument("--supp-xlsx", type=str, default="cui2025_HAR_supp4.xlsx",
                    help="Cui 2025 Supplemental Table 2 (has hg38 + panTro5 HAR coords)")
    ap.add_argument("--no-seq-axes", action="store_true",
                    help="skip ortholog fetch; acceleration falls back to the width proxy, motif=0")
    ap.add_argument("--no-motif", action="store_true",
                    help="compute real acceleration but skip the JASPAR motif scan")
    ap.add_argument("--motif-fpr", type=float, default=1e-4,
                    help="per-motif false-positive-rate threshold for TFBS calls")
    ap.add_argument("--no-temporal", action="store_true",
                    help="Skip the BrainSpan temporal axis (reproduces the pre-temporal v1 spine).")
    ap.add_argument("--sfari", type=str, default=None,
                    help="Optional SFARI gene-list CSV (column 'gene-symbol'); unioned into neurodev set")
    ap.add_argument("--force-download", action="store_true")
    ap.add_argument("--outdir", type=str, default=".")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from har_annotator import (download as dl, data_io, references, filters,
                               evidence, score, temporal, acceleration, motif)

    out = pathlib.Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    # ---- Stage 0: reference tables -----------------------------------------
    print("[0] building reference tables ...")
    neuro = references.build_neurodev(args.ddg2p, force=args.force_download,
                                      sfari_symbols=_sfari_symbols(args.sfari))
    gwas_loci = references.build_gwas_loci(args.gwas_zip, pval_max=args.gwas_pval,
                                           force=args.force_download)
    hars = data_io.load_hars()
    plac = references.build_plac_links(data_io.load_plac_interaction_table(),
                                     force=args.force_download)
    print(f"    neurodev genes={len(neuro)}  gwas loci={len(gwas_loci)}  "
          f"HARs={len(hars)}  plac links={len(plac)}")

    # ---- Stage 1: funnel ----------------------------------------------------
    print("[1] funnel: constraint -> gene proximity -> GWAS ...")
    hars = filters.annotate_phylop(hars)                      # remote bigWig query
    n_all = len(hars)
    hars = filters.filter_constrained(hars, min_phylop_mean=args.min_phylop)
    n_con = len(hars)
    hars = filters.assign_nearest_gene(hars, neuro, window=args.gene_window)
    n_gene = len(hars)
    hars = filters.annotate_gwas(hars, gwas_loci, window=args.gwas_window)
    cand = filters.keep_gwas(hars)
    n_gwas = len(cand)

    funnel = pd.DataFrame({
        "step": ["0. All HARs (Cui 2025, hg38)",
                 f"A. Constrained (phyloP mean > {args.min_phylop})",
                 f"B. Near neurodev gene (<= {args.gene_window//1000} kb TSS)",
                 f"C. Overlaps neuropsych GWAS (<= {args.gwas_window//1000} kb)"],
        "n_hars": [n_all, n_con, n_gene, n_gwas]})
    funnel.to_csv(out / "funnel_counts.csv", index=False)
    cand.to_parquet(out / "candidate_hars.parquet")
    print(funnel.to_string(index=False))

    # ---- Stage 2: evidence spine -------------------------------------------
    print("[2] assembling evidence spine ...")
    ev = evidence.assemble(cand, plac, neuro, dl.DATA_DIR / args.peaks)

    # ---- Stage 2b: temporal axis (developmental timing) --------------------
    if not args.no_temporal:
        lo, hi = (int(x) for x in args.midfetal_window.split(","))
        print(f"[2b] BrainSpan temporal axis (mid-fetal window {lo}-{hi} pcw) ...")
        traj = temporal.build_brainspan_trajectories(
            midfetal=(lo, hi), brainspan_zip=args.brainspan, force=args.force_download)
        ev = temporal.annotate_temporal(ev, traj)
        print(f"    genes timed={ev['gene_peak_pcw'].notna().sum()}  "
              f"peaking in mid-fetal window={int(ev['gene_in_midfetal'].sum())}")

    # ---- Stage 2c: real acceleration + motif disruption --------------------
    # Fetch human (hg38) + chimp (panTro5) HAR orthologs and derive the real
    # substitution burden and JASPAR TF-motif gains/losses. Both replace the
    # earlier proxies (HAR width; motif=0). Sequence fetches are cached.
    if not args.no_seq_axes:
        print("[2c] ortholog sequences -> substitution burden + motif disruption ...")
        coords = acceleration.load_ortholog_coords(dl.DATA_DIR / args.supp_xlsx)
        seqs = acceleration.fetch_ortholog_sequences(
            coords, har_ids=list(ev.har_id),
            cache_path=str(dl.DATA_DIR / "har_ortholog_seqs.parquet"))
        ev = acceleration.annotate_acceleration(ev, seqs)
        if not args.no_motif:
            ev = motif.annotate_motifs(ev, seqs, fpr=args.motif_fpr)
        n_sub = ev["subst_rate"].notna().sum()
        print(f"    sequences={len(seqs)}  subst_rate computed={n_sub}"
              + (f"  motif disruption median={int(ev['motif_disruption'].median())}"
                 if not args.no_motif else "  (motif skipped)"))

    ev.to_parquet(out / "har_evidence.parquet")
    print(f"    evidence table {ev.shape}  plac-linked={ev.gene_assignment_method.eq('plac_linked').sum()}"
          f"  brain-active={ev.brain_dnase_overlap.sum()}")

    # ---- Stage 3: transparent score ----------------------------------------
    print("[3] scoring + ranking ...")
    ranked = score.compute_scores(ev, weights=parse_weights(args.weights),
                                  gene_window=args.gene_window,
                                  gwas_window=args.gwas_window)
    ranked.to_csv(out / "har_shortlist_ranked.csv", index=False)
    ranked.to_parquet(out / "har_shortlist_ranked.parquet")
    print(f"    ranked {len(ranked)} candidates; top: "
          + ", ".join(f"{r.har_id}->{r.gene}" for _, r in ranked.head(5).iterrows()))
    print("done.")
    return ranked


def _sfari_symbols(path):
    if not path:
        return None
    df = pd.read_csv(path)
    col = next((c for c in df.columns if "symbol" in c.lower() or "gene" in c.lower()), df.columns[0])
    return set(df[col].dropna().astype(str))


if __name__ == "__main__":
    main()
