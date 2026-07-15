# Weight sensitivity analysis

*Can the scoring weights be evaluated scientifically? This folder answers that —
and lets you re-run the answer yourself.*

## The short version

The HAR-annotator score is a weighted sum of seven per-axis sub-scores. The seven
weights are **transparent expert priors, not parameters fitted to ground truth** —
because no ground truth exists (validating even one HAR is a multi-year wet-lab
program). So the honest scientific question is not *"are these the right
weights?"* but **"do the conclusions survive reasonable changes to them?"**

They do. This script measures it four ways and finds:

- **The ranking as a whole is robust.** Across 20,000 random weightings, the
  re-ranked list matches the default at **median Spearman rho = 0.97**; even
  equal weights (1/7 each) gives rho = 0.95. *The shortlist is a property of the
  evidence, not of the weight choices.*
- **The exact #1 is a defensible ~3-way race** — ZSWIM6 (~47%), POC1B (~29%),
  TCF20 (~21%), all brain-development genes. The correct claim is "a tight cluster
  of top candidates," not "one winner."
- **No single axis is load-bearing** — dropping any one axis keeps rho >= 0.90
  (except `gene`, which by design changes the question).

## Run it

```bash
# from this folder, in the same env as the pipeline (numpy/pandas/scipy/matplotlib):
python evaluate_weights.py
```

That prints all four tests and writes `figures/fig_weight_sensitivity.png`.

Options:

```bash
python evaluate_weights.py --n 50000          # more Monte-Carlo draws
python evaluate_weights.py --seed 7           # different random seed
python evaluate_weights.py --shortlist PATH   # evaluate a different ranked parquet
python evaluate_weights.py --no-figure        # console only
```

## How it works (and why it's instant)

The shipped shortlist already stores each candidate's seven per-axis sub-scores
(`score_constraint` ... `score_motif`, each in [0, 1]). So the whole ranking can
be recomputed under *any* weight vector as a single matrix-vector product — no
pipeline re-run needed. That's what makes 20,000 re-rankings take a few seconds.

The four tests:

1. **Monte-Carlo perturbation** — draw 20,000 weight vectors from a Dirichlet
   centered on the default, at three spreads (tight / moderate / loose), and
   measure how often the #1 holds, where the default #1 lands, and the rank
   correlation with the default.
2. **Single-axis ablation** — zero each axis in turn, renormalize the other six.
3. **Equal-weights baseline** — all axes = 1/7, the maximally naive prior.
4. **Dominant-axis corners** — push each axis to 0.7 to confirm the axes measure
   different things (they crown different genes, so none is redundant).

## Files

| File | What it is |
|------|-----------|
| `evaluate_weights.py` | The analysis. Self-documented; `--help` for options. |
| `har_shortlist_ranked.parquet` | A copy of the shipped 363-HAR shortlist, so this folder runs standalone. (The script also auto-finds the repo-root copy if you delete this.) |
| `figures/fig_weight_sensitivity.png` | Three-panel summary (regenerated on each run). |
| `requirements.txt` | The four packages needed. |

## The takeaway

This turns a likely objection — *"why these weight numbers?"* — into a strength:
the numbers were tested, and the ranking barely depends on them. The method hands
you a small, biologically coherent set of top candidates rather than false
certainty about one.
