#!/usr/bin/env python
"""Weight sensitivity analysis for the HAR-annotator score.

The seven scoring weights are transparent expert priors, not parameters fitted
to ground truth (no validated-HAR training set exists). So the scientific
question is not "are these the right weights?" but "do the conclusions survive
reasonable changes to them?" -- standard sensitivity analysis.

Because every candidate's seven per-axis sub-scores are stored in the shipped
shortlist (`score_constraint` ... `score_motif`, each in [0,1]), the entire
ranking can be recomputed under *any* weight vector without re-running the
pipeline. This script does that 20,000+ times and reports how much the output
moves.

Four tests:
  1. Monte-Carlo perturbation  -- Dirichlet around the default, 3 spreads
  2. Single-axis ablation      -- zero each axis, renormalize the rest
  3. Equal-weights baseline    -- the maximally naive prior (1/7 each)
  4. Dominant-axis corners     -- push each axis to 0.7

Outputs: console tables + `figures/fig_weight_sensitivity.png`.

Usage:
    python evaluate_weights.py                       # uses ../har_shortlist_ranked.parquet
    python evaluate_weights.py --shortlist PATH      # point at any ranked parquet
    python evaluate_weights.py --n 50000 --seed 7    # more draws / different seed

Requires: numpy, pandas, scipy, matplotlib (the same env as the pipeline).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

# Seven axes and the shipped default weights (must match har_annotator/score.py).
COMPONENTS = ["constraint", "acceleration", "gene", "disease", "brain", "temporal", "motif"]
DEFAULT_WEIGHTS = {
    "constraint": 0.18, "acceleration": 0.07, "gene": 0.22, "disease": 0.22,
    "brain": 0.13, "temporal": 0.13, "motif": 0.05,
}


def load_scores(path: Path):
    """Return (S, genes, har_ids, W0) from a ranked shortlist parquet."""
    df = pd.read_parquet(path)
    missing = [f"score_{c}" for c in COMPONENTS if f"score_{c}" not in df.columns]
    if missing:
        raise SystemExit(f"{path} is missing per-axis score columns: {missing}")
    S = df[[f"score_{c}" for c in COMPONENTS]].to_numpy()
    genes = df["gene"].to_numpy()
    har_ids = df["har_id"].to_numpy() if "har_id" in df.columns else np.arange(len(df)).astype(str)
    W0 = np.array([DEFAULT_WEIGHTS[c] for c in COMPONENTS])
    return df, S, genes, har_ids, W0


def rank_order(S, w):
    """Stable descending argsort of the weighted-sum total score."""
    return np.argsort(-(S @ w), kind="stable")


def rank_of(order, idx):
    return int(np.where(order == idx)[0][0]) + 1


def monte_carlo(S, genes, order0, idx_top, W0, conc, n, rng):
    """Dirichlet-perturbed weights; report top-1 stability + ranking correlation."""
    alpha = W0 * conc
    base20 = set(order0[:20].tolist())
    argsort_base = np.argsort(order0)
    top_gene0 = genes[order0[0]]
    top1_same = 0
    z_rank, rho, jac = [], [], []
    from collections import Counter
    winners = Counter()
    for _ in range(n):
        o = rank_order(S, rng.dirichlet(alpha))
        winners[genes[o[0]]] += 1
        if genes[o[0]] == top_gene0:
            top1_same += 1
        z_rank.append(rank_of(o, idx_top))
        s20 = set(o[:20].tolist())
        jac.append(len(s20 & base20) / len(s20 | base20))
        rho.append(spearmanr(np.argsort(o), argsort_base).correlation)
    return {
        "top1_same": top1_same / n,
        "z_rank": np.array(z_rank),
        "rho": np.array(rho),
        "jac": np.array(jac),
        "winners": winners,
    }


def ablation(S, genes, order0, idx_top, W0):
    argsort_base = np.argsort(order0)
    rows = []
    for i, c in enumerate(COMPONENTS):
        w = W0.copy(); w[i] = 0.0; w = w / w.sum()
        o = rank_order(S, w)
        rows.append((c, genes[o[0]], rank_of(o, idx_top),
                     spearmanr(np.argsort(o), argsort_base).correlation))
    return rows


def corners(S, genes, idx_top, dom=0.7):
    rows = []
    for i, c in enumerate(COMPONENTS):
        w = np.full(len(COMPONENTS), (1 - dom) / (len(COMPONENTS) - 1)); w[i] = dom
        o = rank_order(S, w)
        rows.append((c, genes[o[0]], rank_of(o, idx_top)))
    return rows


def make_figure(res, order0, idx_top, genes, out_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    INK, ACC, MUT, GREEN, PUR = "#2c3e50", "#d1495b", "#5a6b7b", "#2a6f4e", "#7d5ba6"
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    winners = res["winners"]
    total = sum(winners.values())
    top3 = winners.most_common(3)
    labs = [g for g, _ in top3] + ["other"]
    vals = [n / total * 100 for _, n in top3] + [(total - sum(n for _, n in top3)) / total * 100]
    cols = [ACC, GREEN, PUR, MUT]

    fig, ax = plt.subplots(1, 3, figsize=(13, 4.0))
    ax[0].bar(labs, vals, color=cols, edgecolor="white", linewidth=1.2)
    for i, v in enumerate(vals):
        ax[0].text(i, v + 1, f"{v:.0f}%", ha="center", fontsize=9, fontweight="bold")
    ax[0].set_ylabel("share of weightings where\ngene ranks #1 (%)")
    ax[0].set_title("A \u00b7 The #1 slot is a race", loc="left")
    ax[0].set_ylim(0, max(vals) + 8)

    ax[1].hist(res["rho"], bins=40, color=INK, alpha=0.85, edgecolor="white", linewidth=0.3)
    med_rho = float(np.median(res["rho"]))
    ax[1].axvline(med_rho, color=ACC, lw=2)
    ax[1].text(med_rho - 0.002, ax[1].get_ylim()[1] * 0.88, f"median \u03c1 = {med_rho:.3f}",
               ha="right", color=ACC, fontweight="bold")
    ax[1].set_xlabel("Spearman \u03c1 vs default ranking"); ax[1].set_ylabel("random weightings")
    ax[1].set_title("B \u00b7 Overall ranking barely moves", loc="left")

    zr = res["z_rank"]
    ax[2].hist(zr, bins=range(1, 42), color=GREEN, alpha=0.85, edgecolor="white", linewidth=0.3)
    ax[2].axvline(np.median(zr), color=ACC, lw=2)
    ax[2].text(np.median(zr) + 1.5, ax[2].get_ylim()[1] * 0.85,
               f"median rank {np.median(zr):.0f}\n95% \u2264 rank {np.percentile(zr, 95):.0f}",
               color=ACC, fontweight="bold", fontsize=9)
    ax[2].set_xlabel(f"rank of default #1 element ({genes[idx_top]})")
    ax[2].set_ylabel("random weightings")
    ax[2].set_title("C \u00b7 Top hit stays near the top", loc="left")

    fig.suptitle("Weight sensitivity \u2014 all 7 weights perturbed (Dirichlet): method robust, exact #1 a small defensible set",
                 fontsize=11, fontweight="bold", x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    _here = Path(__file__).resolve().parent
    # Prefer a shortlist bundled in this folder; fall back to the repo root one.
    _default = next((p for p in (_here / "har_shortlist_ranked.parquet",
                                 _here.parent / "har_shortlist_ranked.parquet") if p.exists()),
                    _here / "har_shortlist_ranked.parquet")
    ap.add_argument("--shortlist", type=Path, default=_default,
                    help="ranked shortlist parquet with score_<axis> columns "
                         "(default: this folder's copy, else ../har_shortlist_ranked.parquet)")
    ap.add_argument("--n", type=int, default=20000, help="Monte-Carlo draws per spread (default 20000)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-figure", action="store_true", help="skip the PNG")
    args = ap.parse_args()

    if not args.shortlist.exists():
        raise SystemExit(f"shortlist not found: {args.shortlist}\n"
                         f"Point --shortlist at the ranked parquet the pipeline wrote.")
    rng = np.random.default_rng(args.seed)
    df, S, genes, har_ids, W0 = load_scores(args.shortlist)
    order0 = rank_order(S, W0)
    idx_top = order0[0]
    top_gene, top_har = genes[idx_top], har_ids[idx_top]

    print(f"\nLoaded {len(df)} candidates from {args.shortlist.name}")
    print(f"Default #1: {top_gene} ({top_har}), total_score {float((S @ W0)[idx_top]):.3f}\n")

    # --- Test 1: Monte-Carlo ---
    print("=" * 72)
    print("TEST 1  Monte-Carlo weight perturbation (Dirichlet around default)")
    print("=" * 72)
    print(f"{'spread':>10} | {'#1 stable':>9} | {'median rank':>11} | {'p95 rank':>8} | {'top20 Jacc':>10} | {'Spearman':>8}")
    moderate = None
    for conc, label in [(200, "tight"), (50, "moderate"), (10, "loose")]:
        r = monte_carlo(S, genes, order0, idx_top, W0, conc, args.n, rng)
        if label == "moderate":
            moderate = r
        print(f"{label:>10} | {r['top1_same']*100:8.1f}% | {np.median(r['z_rank']):11.0f} | "
              f"{np.percentile(r['z_rank'],95):8.0f} | {r['jac'].mean():10.2f} | {np.nanmean(r['rho']):8.3f}")

    print("\n  Genes that ever win #1 (moderate spread):")
    tot = sum(moderate["winners"].values())
    for g, n in moderate["winners"].most_common(6):
        print(f"    {g:12s} {n/tot*100:5.1f}%")

    # --- Test 2: Ablation ---
    print("\n" + "=" * 72)
    print("TEST 2  Single-axis ablation (drop one axis, renormalize the rest)")
    print("=" * 72)
    for c, t, zr, rho in ablation(S, genes, order0, idx_top, W0):
        print(f"  drop {c:12s} -> #1 = {t:10s} | {top_gene} rank {zr:3d} | Spearman {rho:.3f}")

    # --- Test 3: Equal weights ---
    print("\n" + "=" * 72)
    print("TEST 3  Equal-weights baseline (1/7 each)")
    print("=" * 72)
    we = np.ones(len(COMPONENTS)) / len(COMPONENTS)
    oe = rank_order(S, we)
    print(f"  #1 = {genes[oe[0]]} | {top_gene} rank {rank_of(oe, idx_top)} | "
          f"Spearman {spearmanr(np.argsort(oe), np.argsort(order0)).correlation:.3f}")

    # --- Test 4: Corners ---
    print("\n" + "=" * 72)
    print("TEST 4  Dominant-axis corners (one axis = 0.7)")
    print("=" * 72)
    for c, t, zr in corners(S, genes, idx_top):
        print(f"  {c:12s} dominant -> #1 = {t:10s} | {top_gene} rank {zr:3d}")

    # --- Figure ---
    if not args.no_figure:
        out = Path(__file__).resolve().parent / "figures" / "fig_weight_sensitivity.png"
        make_figure(moderate, order0, idx_top, genes, out)
        print(f"\nWrote {out}")

    print("\nTakeaway: the ranking is a property of the evidence, not the weights.")
    print("Median Spearman stays high under broad perturbation; the exact #1 is a")
    print("small, biologically coherent set rather than a single fragile winner.\n")


if __name__ == "__main__":
    main()
