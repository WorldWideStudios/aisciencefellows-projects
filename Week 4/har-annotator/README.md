# HAR annotator

![CI](https://github.com/nataliegits/har-annotator/actions/workflows/ci.yml/badge.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)

**Human Accelerated Regions (HARs)** are stretches of the genome that stayed
frozen across mammalian evolution and then changed sharply on the human branch,
which makes them prime suspects for what rewired the human brain. There are
thousands of them, most fall in noncoding regulatory sequence, and the hard part
is not finding them but deciding which ones are worth a closer look. This project
is an attempt to do that prioritization honestly: take the full set of HARs and
ask, for each one, whether the evidence actually lines up behind a role in human
neurodevelopment, with every step of the reasoning left visible rather than hidden
inside a model. The pipeline narrows the HARs to constrained,
neurodevelopment-adjacent, disease-overlapping elements, assembles a per-element
evidence table, ranks the survivors with a transparent additive score where each
axis's contribution stays inspectable, and reads out the top candidates with an
antagonistic-pleiotropy framing. The aim is a defensible shortlist of hypotheses,
not a black-box answer.

Everything is hg38. Every data pull is cached, hashed, and logged to
`data/manifest.csv`, so the analysis replays end-to-end from source.

> **Built with [Claude Science](https://www.anthropic.com).** This pipeline was
> developed end-to-end with Anthropic's scientific-computing agent — from writing
> and iterating the scoring modules, to querying a 9.6 GB conservation file
> remotely, to fact-checking the top candidates against the scored tables, to
> re-running the whole thing byte-for-byte and generating every figure. See
> [How this was built](#how-this-was-built-with-claude-science) for the details.
> The glass box extends to how the box itself was made.

```
python run_pipeline.py            # reproduces the shipped shortlist exactly
```

> **Looking for v2?** This README documents **v1**, the disease-anchored
> pipeline. The [`v2/`](v2/) folder holds the **discovery-mode** build-out —
> same pipeline with the disease-gene gate removed — plus a neglect-aware
> ranking and a wet-lab validation plan. Start at [`v2/README_v2.md`](v2/README_v2.md),
> or jump to [the v2 section below](#v2--discovery-mode-and-beyond). v1 is
> unchanged; v2 is purely additive.

---

## What This Pipeline Does

HARs are stretches of DNA that stayed nearly frozen across mammals for millions
of years, then changed suddenly in the human lineage. There are 3,257 of them,
and most have no known function. This pipeline asks a narrower question: *which
of these human-accelerated regions are the best candidates for shaping human
brain development?*

It works in five moves:

1. **Filter (Phase 1).** Start from all 3,257 HARs and keep only those that pass
   three tests in a row: evolutionarily constrained, sitting near a gene already
   known to cause a neurodevelopmental disorder, and overlapping a genetic signal
   for a brain-related trait. That drops 3,257 → **363**.
2. **Gather evidence (Phase 2).** For each of the 363 survivors, record *how
   strong* every line of evidence is: how conserved, which disease gene and how
   close, how significant the trait signal, whether it's active in fetal brain
   tissue, whether that gene is busiest during mid-fetal development, how much its
   sequence diverged from chimpanzee, and how many transcription-factor binding
   sites it disrupts.
3. **Score (Phase 3).** Collapse that evidence into one number per HAR, a
   transparent weighted sum, with every axis's contribution kept visible, and
   rank them best-to-worst.
4. **Interpret (Phase 4).** Read the top of the list and check that the ranking
   makes biological sense, gene by gene.
5. **Visualize & package (Phases 5–6).** Draw the figures and bundle everything
   into a rerunnable package.

**One honest precision.** This does *not* discover new disease genes. The disease
genes came *in* as a filter (step 1 requires proximity to a known
neurodevelopmental-disorder gene). What gets ranked is the **regulatory
regions**: the output is a shortlist of candidate HARs, i.e. hypotheses about
*which human-accelerated elements are worth studying* for a role in human brain
development during fetal gestation. The genes are the input; the HARs are the
result.

That disease-gene filter is also this pipeline's built-in blind spot — by
construction it can *never* surface a HAR near a gene that isn't yet linked to
disease. Removing that one gate is exactly what the discovery-mode build-out in
[`v2/`](v2/) does: same pipeline, same seven axes, but scoring every HAR near
*any* gene. It preserves all 363 of these ranks unchanged and adds **214 new
candidate elements** near genes the disease filter was structurally hiding
(*DAB1, NPAS3, TLE4, PTPRD, CDH8*, …). See [`v2/README_v2.md`](v2/README_v2.md)
or [the v2 section below](#v2--discovery-mode-and-beyond).

---

## What it does: the funnel

| Step | Filter | HARs |
|------|--------|------|
| 0 | All HARs (Cui et al. 2025, *Nature*, hg38) | 3,257 |
| A | Mammalian constraint, mean 241-way phyloP > 1.0 | 2,757 |
| B | Within 1 Mb of a neurodevelopmental-disorder gene TSS | 1,718 |
| C | Within 25 kb of a genome-wide-significant neuropsychiatric GWAS lead SNP | **363** |

The 363 candidates are then scored on seven axes and ranked. Top candidate:
**HAR_2378 → *ZSWIM6*** (rank 1, total score 0.618 — highly constrained, the
strongest real human–chimp acceleration signal in the top tier, embryonic-brain
DNase-active), with **HAR_575 → *POC1B*** and **HAR_1826 → *TCF20*** essentially
tied just behind (0.605 each). Classic neurodevelopmental / human-evolution genes
recovered in the shortlist include *ZEB2, TCF4, MEF2C, PHOX2B, TCF20, ZSWIM6,
FOXP2, SOX5, NR4A2, MITF*. The seventh axis, **temporal**, adds a
developmental clock: how concentrated each target gene's prenatal expression is
in the mid-fetal convergence window (~10–24 post-conception weeks, BrainSpan),
the developmental moment where human-specific regulation and neuropsychiatric
risk are thought to coincide. Of the 363 candidates, 347 target genes could be
timed and 129 peak inside the mid-fetal window.

<img width="1801" height="1231" alt="fig_shortlist_preview" src="https://github.com/user-attachments/assets/cc2032b0-7940-4a23-8bc2-63c1d57200ef" />


*Because the score is a transparent weighted sum, every rank decomposes into its
seven axes — you can see precisely what earns each element its place (ZSWIM6's
distinguishing acceleration signal; POC1B riding its disease axis; the motif axis
near-zero across the board, the pipeline flagging where it is least certain).*

---

## The transparent score

The total is a **weighted sum of seven normalized (0–1) component scores**, no
black box. Every `score_<c>` and its weighted `contrib_<c>` is retained as a
column, so `total_score` decomposes exactly (verified: max reconstruction
error 0.0).

```
total_score = Σ  WEIGHTS[c] · score_c        (c in the seven components below)
```

| Component | Default weight | Evidence |
|-----------|:-:|----------|
| `constraint`   | 0.18 | mean 241-way phyloP, min-max scaled |
| `gene`         | 0.22 | DDG2P confidence tier × TSS-distance decay, +0.15 if PLAC-seq-linked |
| `disease`      | 0.22 | −log10(GWAS p) × proximity to lead SNP |
| `brain`        | 0.13 | ENCODE embryonic-brain DNase peak overlap (+ PLAC-seq ATAC support), *where* |
| `temporal`     | 0.13 | fraction of target gene's prenatal expression in the mid-fetal window (BrainSpan), *when* |
| `acceleration` | 0.07 | real human–chimp substitution rate from the panTro5 ortholog alignment (subs / aligned bp), min-max scaled |
| `motif`        | 0.05 | JASPAR TF-motif sites gained + lost between the human and chimp alleles, min-max scaled |

Weights sum to 1.0 and are module constants (`har_annotator/score.py`),
overridable per run: `python run_pipeline.py --weights gene=0.35,disease=0.30`.
`brain` (*where* a target gene is active) and `temporal` (*when* it is active)
are the paired developmental-context axes.

<a name="the-seven-formulas"></a>
### The seven formulas at a glance

Every axis maps its raw evidence onto **0–1 with one explicit transform** — no
learned model, no hidden step. Here is the exact arithmetic for all seven, the
whole scoring engine on one screen:

| Axis | Weight | `score` (0–1) = | in words |
|------|:-:|---|---|
| **gene** | 0.22 | `confidence × (1 − dist/1 Mb) + 0.15·plac`, clip [0,1] | disease-gene tier (def 1.0 / strong 0.75 / mod 0.5 / lim 0.3), faded by TSS distance, +0.15 if physically contacted (PLAC-seq) |
| **disease** | 0.22 | `min(−log₁₀ p, 50)/50 × (1 − dist/25 kb)` | GWAS significance × closeness to the lead SNP — needs **both** |
| **constraint** | 0.18 | `minmax(phyloP_mean)` | how conserved, rescaled 0–1 across the candidate set |
| **brain** *(where)* | 0.13 | `0.8·dnase_overlap + 0.2·plac_atac` | in fetal-brain open chromatin (+ neuronal ATAC support) |
| **temporal** *(when)* | 0.13 | `gene_midfetal_frac`, clip [0,1] | fraction of the gene's prenatal expression inside 10–24 pcw |
| **acceleration** | 0.07 | `minmax(subst_rate)` | human–chimp substitutions per aligned bp, rescaled 0–1 |
| **motif** | 0.05 | `minmax(motif_disruption)` | # JASPAR TF sites gained/lost between the human and chimp alleles, rescaled 0–1 |

```
total_score = Σ  WEIGHTS[axis] · score_axis      # 7 terms, sums to a 0–1 number
```

Two design choices are visible right in the table: **`constraint`,
`acceleration`, and `motif` are min-max scaled** (relative to the candidate set,
so they answer "compared to the other candidates"), while **`gene`, `disease`,
`brain`, and `temporal` use fixed absolute transforms** (they mean the same thing
regardless of which HARs are in the funnel). Worked example — POC1B's gene axis:
`1.0 × (1 − 0/1 Mb) + 0.15 = 0.974`. The per-axis prose below walks through each
one; this table is the reference you can pull up in one glance.

### How we weighted the values and gave each a 0–1 score

Each axis goes through two steps: first the raw evidence is transformed into a
**normalized 0–1 score** (so a phyloP of 5.0 and a p-value of 1e-40 live on the
same scale), then that score is multiplied by a **weight** that says how much
the axis counts toward the total. Both numbers are kept as columns
(`score_<c>` and `contrib_<c>`), so nothing is hidden. Listed
heaviest-weighted first:

1. **gene, weight 0.22.** Score = `confidence × distance_decay + plac_boost`.
   The DDG2P tier becomes a number (definitive 1.0 → strong 0.75 → moderate 0.5
   → limited 0.3), multiplied by `1 − distance/1Mb` (a gene at the HAR ≈ 1, one
   at the 1 Mb edge ≈ 0), plus a flat **+0.15** if the gene came from a
   PLAC-seq physical contact rather than mere proximity. Clipped to [0,1]. Tied
   for the highest weight because gene-link quality is core to the hypothesis.
2. **disease, weight 0.22.** Score = `significance × proximity`. Significance
   is −log₁₀(p), capped at 50 then divided by 50 (p=5e-8 weak → p=1e-50 maxed);
   proximity is `1 − gwas_distance/25kb`. Multiplied, so a HAR needs **both** a
   strong signal **and** to sit close to the lead SNP. Tied at the top with
   gene, together they define the biological question.
3. **constraint, weight 0.18.** Score = min-max scaled `phylop_mean` across
   the 363 candidates (least-constrained → 0, most → 1). The evolutionary
   anchor, just below the two biological axes.
4. **brain "where", weight 0.13.** Score = `0.8 × dnase_overlap + 0.2 ×
   plac_atac`. Mostly the ENCODE embryonic-brain DNase overlap (0.8), topped up
   by PLAC-seq ATAC support (0.2); a HAR in fetal-brain open chromatin with
   neuronal ATAC support reaches 1.0. One of the paired developmental-context
   axes.
5. **temporal "when", weight 0.13.** Score = `gene_midfetal_frac`, the
   fraction of the target gene's prenatal expression falling inside the
   mid-fetal window (10–24 pcw), clipped to [0,1]; no BrainSpan trajectory → 0.
   Weighted equal to brain, its "where/when" partner.
6. **acceleration, weight 0.07.** Score = min-max scaled `subst_rate`, the
   human–chimp substitution rate: we fetch each HAR's human (hg38) and
   chimpanzee (panTro5) orthologous sequence, align them, and count
   substitutions per aligned bp. Weight stays low at 0.07 because divergence is
   not lineage-polarized (see caveat below).
7. **motif, weight 0.05.** Score = min-max scaled `motif_disruption`, the
   number of JASPAR transcription-factor binding sites **gained or lost**
   between the human and chimp alleles (scan both sequences against 879
   JASPAR2024 CORE vertebrate motifs at a per-motif false-positive rate of
   1e-4; a site "present" in one allele but not the other counts as a
   disruption). This is the direct sequence-to-function signal, which TF
   binding sites the human-specific changes create or destroy. Previously
   hard-coded to 0; now live.

The seven weights sum to 1.0, so the **total_score** is itself a 0–1 number:
`Σ WEIGHTS[c] · score_c`. Every weighted piece (`contrib_c`) is retained, so
the total adds back up exactly (verified at 0.0 reconstruction error) and you
can see precisely how many points each axis gave each HAR. Two properties are
worth keeping in mind: the weights are hand-set priors, overridable with
`--weights`; and three axes (`constraint`, `acceleration`, and `motif`) are
scaled *relative to the candidate set* (min-max), while `gene`, `disease`,
`brain`, and `temporal` use fixed, absolute transforms that do not shift when
the funnel changes.

**Note on the temporal axis and reproducibility.** Adding `temporal` as a
seventh axis re-normalized the six original weights, so the default ranking now
incorporates the developmental clock and differs from the pre-temporal v1
shortlist (this is intended; it is the whole point of the axis). To reproduce
the exact pre-temporal v1 ranking, run with `--no-temporal`, which skips the
BrainSpan stage and restores the six-axis spine.

**The acceleration and motif axes are direct sequence measurements.**
`acceleration` is the human–chimp substitution rate (substitutions per aligned
base pair, from globally aligned hg38 / panTro5 orthologs); `motif` is the count
of JASPAR2024 TF-binding sites gained or lost between the two alleles. Both are
computed per candidate. How sensitive the final ranking is to the seven axis
weights is quantified in the [`weight_eval/`](weight_eval/) package
(`python weight_eval/evaluate_weights.py`) — summarized next.

### Are the weights arbitrary? (weight sensitivity)

The seven weights are **transparent expert priors, not parameters fitted to
ground truth** — no validated-HAR training set exists to fit them to. So the
honest question isn't *"are these the right weights?"* but *"do the conclusions
survive reasonable changes to them?"* Because every candidate's seven per-axis
sub-scores are stored in the shortlist, the whole ranking can be recomputed under
any weight vector without re-running the pipeline — so this is directly testable.

Perturbing all seven weights across 20,000 random weightings (Dirichlet around
the default):

- **The ranking as a whole is robust** — median Spearman **ρ = 0.97** vs the
  default (equal weights, 1/7 each, still gives ρ = 0.95). *The shortlist is a
  property of the evidence, not of the weight choices.*
- **The exact #1 is a defensible ~3-way race** — ZSWIM6 (~47%), POC1B (~29%),
  TCF20 (~21%), all neurodevelopmental genes. The tool hands you a small,
  coherent cluster of top candidates rather than false certainty about one.
- **No single axis is load-bearing** — dropping any one axis keeps ρ ≥ 0.90
  (except `gene`, which by design changes the question being asked).

Reproduce it yourself: the [`weight_eval/`](weight_eval/) folder ships a
standalone script (`python weight_eval/evaluate_weights.py`) that runs all four
tests and regenerates the summary figure.

---

## Install & run

```bash
# conda env (Python 3.11; pyranges pins <3.13)
conda create -n hars -c bioconda -c conda-forge python=3.11 \
    pandas numpy scipy matplotlib seaborn requests \
    pyranges=0.1.4 pybigwig biopython pyarrow openpyxl
conda activate hars

python run_pipeline.py                     # defaults, reproduces shipped outputs
python run_pipeline.py --gwas-window 50000 # sensitivity: wider disease window
python run_pipeline.py --min-phylop 1.5 --gene-window 500000
python run_pipeline.py --weights disease=0.35,gene=0.20 --outdir alt_weights/
```

Key parameters (all have defaults that reproduce the shipped shortlist):

| Flag | Default | Meaning |
|------|:-:|---------|
| `--min-phylop`   | 1.0 | Step A constraint threshold (mean phyloP) |
| `--gene-window`  | 1_000_000 | Step B max HAR–TSS distance (bp) |
| `--gwas-window`  | 25_000 | Step C max HAR–lead-SNP distance (bp) |
| `--gwas-pval`    | 5e-8 | GWAS genome-wide significance cutoff |
| `--weights`      | - | override score weights, `k=v,k=v` |
| `--midfetal-window` | 10,24 | mid-fetal convergence window (post-conception weeks) for the temporal axis |
| `--no-seq-axes`  | off | skip the ortholog fetch; acceleration falls back to the width proxy and motif = 0 (reproduces the pre-upgrade axes) |
| `--no-motif`     | off | compute real acceleration but skip the JASPAR motif scan |
| `--motif-fpr`    | 1e-4 | per-motif false-positive rate for TF-binding-site calls |
| `--no-temporal`  | off | skip the BrainSpan temporal axis (reproduces the pre-temporal v1 spine) |
| `--brainspan`    | - | optional local BrainSpan zip path (else fetched from Allen Institute) |
| `--sfari`        | - | optional SFARI gene CSV, unioned into the neurodev set |
| `--force-download` | off | re-fetch all sources instead of using the cache |

GWAS-window sensitivity (candidate count): 10 kb → 196, **25 kb → 363**,
50 kb → 526, 100 kb → 759. 25 kb (LD-block scale) is the shipped default.

---

## Change the weights yourself

The score is a plain weighted sum, so re-prioritizing the shortlist is a
one-liner — no retraining, no code edit required. There are two ways in,
depending on whether you want a one-off run or a new default.

**1. Per run, from the command line (no code edit).** Pass `--weights` as a
comma-separated `axis=value` list. Any axis you name is overridden; every axis
you *don't* name keeps its default:

```bash
# reward TF-motif disruption instead of gene/disease proximity
python run_pipeline.py --weights motif=0.30 --outdir out_motif/

# a "development-first" lens: push the where/when axes
python run_pipeline.py --weights brain=0.25,temporal=0.25 --outdir out_dev/

# reproduce the pre-temporal v1 ranking (turn one axis off entirely)
python run_pipeline.py --weights temporal=0 --outdir out_v1spine/
```

The seven axis names are exactly: `constraint`, `gene`, `disease`, `brain`,
`temporal`, `acceleration`, `motif`. Each run writes its own full ranked table
to `--outdir`, so you can diff two weightings and see exactly which HARs moved.

**2. As a new default, in code.** Edit the `WEIGHTS` dict at the top of
[`har_annotator/score.py`](har_annotator/score.py):

```python
WEIGHTS = {
    "constraint": 0.18, "gene": 0.22, "disease": 0.22,
    "brain": 0.13, "temporal": 0.13, "acceleration": 0.07, "motif": 0.05,
}
```

Change the numbers, re-run `python run_pipeline.py`, and every downstream
output (shortlist, evidence table, figures) picks up the new default.

**One thing to know about the math.** Overrides *merge onto* the defaults —
`w = {**WEIGHTS, **your_overrides}` — they are **not** renormalized to sum to
1.0. So `--weights motif=0.30` leaves the other six axes at their defaults and
the totals no longer sum to 1. That does **not** distort the ranking (it's a
monotonic rescale — every HAR is scored on the same weights), but if you want
the `total_score` to stay a clean 0–1 number, pass a full set that sums to 1.0.
The demo's "push one axis to 0.30 and shrink the rest proportionally" behavior
(see `fig_weight_knobs.png`) is exactly that renormalized version.

**How much do the weights actually matter?** See
[*Are the weights arbitrary?*](#are-the-weights-arbitrary-weight-sensitivity)
below: across 20,000 random weightings the shortlist is stable (ρ ≈ 0.95 even
at equal 1/7 weights), so the weights are a steering interface, not a lever for
manufacturing a result.

---

## v2 — discovery mode (and beyond)

Everything above describes **v1**: the funnel *requires* each HAR to sit near a
known neurodevelopmental **disease** gene, so every hit has a disease name
attached by construction. That is deliberately conservative — and it means the
truly novel elements (accelerated, brain-active, but near a gene nobody has
linked to disease yet) are filtered out before they are ever scored.

The [`v2/`](v2/) folder relaxes that. It keeps v1 completely intact and adds
three things on top:

- **Discovery mode (v2.0).** Drop the disease-gene gate; require proximity to
  *any* gene instead. Same constraint gate, same GWAS overlap, same seven scoring
  axes. The result is a **strict superset**: the shipped **363** disease-anchored
  elements keep their exact ranking (Spearman ρ = 0.9998, ZSWIM6 still #1), and
  **214 new elements surface** — 577 total — every one near a gene *not* in the
  disease panel. The new hits read like a who's-who of cortical development the
  disease panel hasn't caught up to: *DAB1* (reelin / cortical layering), *NPAS3*
  (schizophrenia), *TLE4*, *PTPRD*, *CDH8*, *EFNA5*, *TSHZ2/3*.
- **Neglect-aware ranking (v1.1).** An optional axis that rewards *understudied*
  target genes (`1 − minmax(log10(PubMed + 1))`), folded in so the weights still
  sum to 1.0. It turns "find me something new" into an explicit knob.
- **A wet-lab validation ladder.** MPRA → Capture-C + CRISPRi → humanized
  cortical organoids — the arc from an in-silico hypothesis to a mechanistic
  claim.

### What's in `v2/`

| File | What it is |
|------|-----------|
| [`v2/README_v2.md`](v2/README_v2.md) | v2 README — discovery mode, no disease requirement |
| `v2/demo_live_v2.py` | live demo, superset of v1's `demo_live.py` (adds `--discovery`, `--neglect W`) |
| `v2/har_shortlist_discovery.parquet` / `.csv` | the full 577-element discovery shortlist |
| `v2/discovery_new_elements.csv` | the 214 newly-surfaced elements on their own |
| `v2/har_shortlist_neglect.parquet` / `.csv` | the neglect-aware re-ranking |
| `v2/validation_ladder.md` | the 4-tier wet-lab validation plan |
| `v2/figures/` | discovery-vs-anchored, neglect-reshuffle, and validation-ladder figures |

```bash
python v2/demo_live_v2.py --discovery      # the 577-element discovery shortlist, live
python v2/demo_live_v2.py --neglect 0.25   # reward understudied target genes
```

**When to use which.** Use **v1** when you want conservative, disease-grounded
candidates. Use **v2 discovery** when you want reach into un-annotated biology —
accepting that the 214 new elements have no disease prior and are best read as
leads for follow-up. See [`v2/README_v2.md`](v2/README_v2.md) for the full v2
write-up and caveats.

---

## Data sources

All fetched, versioned, and hashed in `data/manifest.csv` (URL + access date +
SHA-256 + size). See `phase0_sources.md` for the full provenance / de-risking
notes.

| Source | Used for | manifest row | builder / consumer |
|--------|----------|:-:|:-:|
| **HARs & PLAC-seq**, Cui et al. 2025, *Nature* | 3,257 HARs, hg38-native; neuronal PLAC-seq HAR→gene links | `hars_bed`, `hars_meta`, `cui2025_supp4` | `data_io.py`, `references.build_plac_links` |
| **Constraint**, Zoonomia 241-way phyloP | per-HAR mean/max phyloP | *(remote query, not cached)* | `filters.annotate_phylop` |
| **Neurodev genes**, DDG2P (Gene2Phenotype) | 2,524 genes → hg38 coords + confidence tier | `ddg2p`, `refgene_hg38` | `references.build_neurodev` |
| **GWAS**, EBI GWAS Catalog (ontology-annotated) | 22,489 genome-wide-sig neuropsychiatric lead SNPs | `gwas_assoc` | `references.build_gwas_loci` |
| **Developing brain**, ENCODE embryonic-brain DNase-seq | 165,568 peaks; regulatory-activity axis (*where*) | `fetal_brain_dnase` | `evidence.annotate_brain_dnase` |
| **Developmental transcriptome**, BrainSpan (Allen Institute) | per-gene prenatal expression → mid-fetal timing axis (*when*) | `brainspan_devtx` | `temporal.build_brainspan_trajectories` |
| **Gene coords**, UCSC refGene hg38 | gene symbol → strand-aware TSS | `refgene_hg38` | `references.build_genes` |
| **HAR orthologs**, UCSC sequence API (hg38 + panTro5) | per-HAR human/chimp sequence → substitution rate (acceleration axis) | `har_ortholog_seqs` | `acceleration.py` |
| **TF motifs**, JASPAR2024 CORE vertebrates (879 PWMs, via `pyjaspar`) | TF-binding sites gained/lost between alleles (motif axis) | `jaspar_thresholds` | `motif.py` |

Every raw file's exact download URL, SHA-256, access date, and size is in
`data/manifest.csv`; `phase0_sources.md` has the full de-risking notes. The
raw files themselves are **not committed** (see `.gitignore`), `download.py`
re-fetches and hash-verifies them from the URLs below.

### Primary references & direct links

- **HARs & PLAC-seq map, Cui et al. (2025), *Nature* 640:991–999.**
  "Comparative characterization of human accelerated regions in neurons,"
  doi:[10.1038/s41586-025-08622-x](https://doi.org/10.1038/s41586-025-08622-x).
  Supplies both the 3,257 HAR coordinates **and** the neuronal PLAC-seq HAR→gene
  map: they are the same table, not separate downloads. That table is the
  paper's **Supplementary Table 2** ("HAR and their chimpanzee ortholog
  interacting genes in neurons"); the map used here is its "Table-b: Genes
  interacting with HARs in human" sheet (1,303 HARs, 1,719 genes,
  genome-wide). **Note on numbering:** the download file is named
  `41586_2025_8622_MOESM4_ESM.xlsx` (Nature's *MOESM4* file id), but the table
  it contains is Supplementary Table **2**, the MOESM file number and the
  supplementary-table number do not correspond. This is *not* Supplementary
  Table 3, which is the separate CRISPRi-prioritized shortlist of ~20 HARs
  selected for functional validation. Fetched via the GitHub mirror
  [`athenamarou/HAR-TFBS-Project`](https://github.com/athenamarou/HAR-TFBS-Project)
  (`data/hars_hg38.bed`, `data/hars_hg38.tsv`,
  `data/supplementary/41586_2025_8622_MOESM4_ESM.xlsx`).

  **Method note:** the HAR→gene links come from **PLAC-seq** (proximity
  ligation-assisted ChIP-seq, anchored on the H3K4me3 active-promoter mark) in
  human and chimpanzee iPSC-derived neurons, a ChIP-anchored chromatin-contact
  assay, *not* generic Hi-C. Earlier drafts of this project called it "Hi-C";
  that was imprecise and has been corrected throughout, including the column
  names (`plac_gene`, `plac_type`, `plac_atac`, assignment `plac_linked`).
- **Neurodevelopmental gene list: DDG2P, from Gene2Phenotype (G2P).**
  Download: `https://ftp.ebi.ac.uk/pub/databases/gene2phenotype/G2P_data_downloads/2026_06_28/DDG2P_2026-06-28.csv.gz` (EBI).
  Portal: [www.ebi.ac.uk/gene2phenotype](https://www.ebi.ac.uk/gene2phenotype).
  Primary paper: Thormann *et al.* (2024), *Genome Medicine*: "Curating genomic
  disease-gene relationships with Gene2Phenotype (G2P)",
  doi:[10.1186/s13073-024-01398-1](https://doi.org/10.1186/s13073-024-01398-1)
  ([PMC11539801](https://pmc.ncbi.nlm.nih.gov/articles/PMC11539801/)); earlier
  G2P/VEP tool paper: Thormann *et al.* (2019), *Nature Communications*,
  doi:[10.1038/s41467-019-10016-3](https://doi.org/10.1038/s41467-019-10016-3).
- **Developing-brain open chromatin: ENCODE DNase-seq `ENCFF660HML`.**
  Peak file: [encodeproject.org/files/ENCFF660HML](https://www.encodeproject.org/files/ENCFF660HML/)
  (download: `@@download/ENCFF660HML.bed.gz`); parent experiment
  [ENCSR420RWU](https://www.encodeproject.org/experiments/ENCSR420RWU/)
  (brain, male embryo 105 days). Portal paper: Davis *et al.* (2018),
  *Nucleic Acids Research*: "The Encyclopedia of DNA Elements (ENCODE): data
  portal update", doi:[10.1093/nar/gkx1081](https://doi.org/10.1093/nar/gkx1081);
  consortium: The ENCODE Project Consortium (2012), *Nature*,
  doi:[10.1038/nature11247](https://doi.org/10.1038/nature11247).
- **Developmental transcriptome: BrainSpan Atlas of the Developing Human Brain**
  (Allen Institute for Brain Science). "RNA-Seq Gencode v10 summarized to genes."
  Portal / download: [www.brainspan.org](https://www.brainspan.org)
  (Developmental Transcriptome → Download). Primary paper: Miller *et al.* (2014),
  *Nature* 508:199–206: "Transcriptional landscape of the prenatal human brain",
  doi:[10.1038/nature13185](https://doi.org/10.1038/nature13185)
  ([PMC4105188](https://pmc.ncbi.nlm.nih.gov/articles/PMC4105188/)). Used for the
  `temporal` axis: per-gene prenatal expression trajectories and the fraction
  falling in the mid-fetal convergence window (~10–24 pcw).
- **Neuropsychiatric GWAS: NHGRI-EBI GWAS Catalog** (ontology-annotated
  associations, latest release).
  Download: `https://ftp.ebi.ac.uk/pub/databases/gwas/releases/latest/gwas-catalog-associations_ontology-annotated-full.zip`;
  portal [www.ebi.ac.uk/gwas](https://www.ebi.ac.uk/gwas).
  Papers: Cerezo *et al.* (2025), *Nucleic Acids Research* 53(D1):D998–D1005,
  doi:[10.1093/nar/gkae1070](https://doi.org/10.1093/nar/gkae1070) (current
  release); Sollis *et al.* (2023), *NAR* 51(D1):D977–D985,
  doi:[10.1093/nar/gkac1010](https://doi.org/10.1093/nar/gkac1010).
  **"Neuropsychiatric" is a keyword filter, not a Catalog category.**
  `references.build_gwas_loci` selects rows whose `MAPPED_TRAIT`/`DISEASE/TRAIT`
  match `references._NEURO_PAT` (schizophren·autis·bipolar·depress·neurotic·
  cognit·educational·intellig·attention-deficit/adhd·alzheimer·neurodevelop·
  intellectual-disab·epileps·tourette·obsessive) and keeps genome-wide-
  significant hits (p < 5×10⁻⁸) → 22,489 lead SNPs. The term list is a module
  constant and is meant to be edited. **Trait-mix caveat:** the largest
  contributors are *educational attainment*, *intelligence*, and *cognitive-
  function* GWAS, behavioural/cognitive proxies with known social-environmental
  confounding. "Overlaps an educational-attainment locus" is therefore a weaker
  biological claim than "overlaps a schizophrenia locus"; the shipped
  `mapped_trait` column lets you see which applies to each candidate.
- **Constraint: Zoonomia 241-way phyloP** (Cactus 241-mammal alignment),
  queried remotely from the UCSC bigWig (`hg38 cactus241way`); 9.6 GB, never
  downloaded. The phyloP scores themselves: Christmas *et al.* (2023),
  *Science* 380:eabn3943, "Evolutionary constraint and innovation across
  hundreds of placental mammals,"
  doi:[10.1126/science.abn3943](https://doi.org/10.1126/science.abn3943).
  Disease-mapping utility of base-pair mammalian constraint: Sullivan *et al.*
  (2023), *Science* 380:eabn2937,
  doi:[10.1126/science.abn2937](https://doi.org/10.1126/science.abn2937).
- **Gene coordinates: UCSC refGene (hg38).**
  `https://hgdownload.soe.ucsc.edu/goldenPath/hg38/database/refGene.txt.gz`.

**TF-motif note.** The `motif` score component (weight 0.05) is **live**. Both
the human (hg38) and chimp (panTro5) HAR alleles are scanned against the 879
JASPAR2024 CORE vertebrate PWMs (`pyjaspar`) at a per-motif false-positive rate
of 1e-4; a binding site present in one allele but not the other counts as a
gain or loss, and `motif_disruption` = gains + losses drives the axis
(min-max scaled). The recurrently gained/lost factors across candidates are
neurodevelopmental regulators (MEIS1/2, PBX3, PKNOX1, DLX1, POU/SOX2, MEF2A).
This is a candidate-level, presence/absence call, not an affinity model; see
caveat 4.

---

## Package layout

```
har_annotator/
  download.py    cached + hashed + manifest-logged fetches
  data_io.py     load HAR base table + Cui PLAC-seq sheet from the supplement
  references.py  build derived tables: genes, neurodev (DDG2P), GWAS loci, PLAC-seq links
  filters.py     Phase-1 funnel: annotate_phylop, filter_constrained,
                 assign_nearest_gene, annotate_gwas, keep_gwas
  evidence.py    Phase-2 per-element evidence spine (assemble)
  temporal.py    Phase-2b developmental-timing axis (build_brainspan_trajectories, annotate_temporal)
  acceleration.py Phase-2c human–chimp substitution rate (fetch_ortholog_sequences, align_and_count, annotate_acceleration)
  motif.py       Phase-2c JASPAR TF-motif gain/loss scan (load_pssms, compute_fpr_thresholds, annotate_motifs)
  score.py       Phase-3 transparent additive score (compute_scores, WEIGHTS)
run_pipeline.py  end-to-end driver (parameterized)
```

Outputs, by phase:

| Phase | Output artifact(s) | What it is |
|-------|--------------------|------------|
| 1: funnel | `funnel_counts.csv`, `candidate_hars.parquet` | the 3,257→363 attrition and the surviving candidates |
| 2: evidence | `har_evidence.parquet` (+ `har_evidence_schema.json`) | per-element evidence table (363 × 40), no score |
| 3: score | `har_shortlist_ranked.csv`/`.parquet`, `har_shortlist_top50.csv` | the same rows plus every axis score, contribution, and `total_score`, ranked |
| 4: interpret | `top_candidates_interpretation.md` | per-HAR biology for the top candidates, in tiers, with caveats |
| 5: figures | see below | five figures |

Figures (Phase 5): `fig_funnel.png` (candidate attrition),
`fig_score_overview.png` (per-axis score contributions + score distribution),
`fig_top_candidate_detail.png` (top HAR at its locus),
`fig_acceleration_dist.png` (human–chimp substitution rates across the
candidate set), `fig_motif_disruption.png` (JASPAR motif gains/losses +
most recurrently disrupted TFs).

---

## What "mammalian constraint" means here

**phyloP** (phylogenetic P-value) is a per-base evolutionary-rate score. For
each position in the human genome, it compares the substitution rate observed
across an alignment of 241 placental mammals against the rate expected under
neutral drift. Positive = **slower than neutral** = the base has been conserved
= *constrained* (purifying selection removed mutations there). Negative = faster
than neutral (accelerated); ~0 = evolving neutrally. The scores come from the
Zoonomia Cactus 241-mammal alignment (Christmas et al. 2023). We take the
**mean phyloP over each HAR's span** as its constraint value and keep HARs with
mean > 1.0 (Step A: 3,257 → 2,757).

Why constraint matters for a *human-accelerated* region: the apparent paradox
is the point. A HAR is a locus that was **deeply conserved across mammals**
(high ancestral constraint) yet **changed rapidly on the human branch**. The
mammalian-constraint filter enriches for elements that were doing something
selectively important for a long time; the human-specific change is then more
likely to be functionally consequential than a change in a locus that was
never constrained. Constraint (mammalian, phyloP) and acceleration
(human-branch) are **different axes**: this pipeline scores constraint
directly (mammalian phyloP) and acceleration directly from the human–chimp
substitution rate, with the caveat that the latter is not lineage-polarized.

**"Sharpened disease mapping": what's actually established vs. what we
verified here.** The strong, external result is that base-pair mammalian
constraint from Zoonomia enriches for trait/disease heritability and improves
prioritization of causal variants, shown genome-wide in Sullivan et al. (2023,
*Science*, doi:10.1126/science.abn2937), not something this pipeline proves. To
avoid overclaiming, the enrichment was checked **inside this dataset**: of all
3,257 HARs, constrained ones (phyloP > 1) overlap a neuropsychiatric GWAS locus
(±25 kb) at **21.0%** vs **15.4%** for unconstrained, a **1.37× enrichment**
(Fisher odds 1.46, p = 3.6×10⁻³). So constraint does concentrate disease
overlap in our HAR set, but **modestly**; it is a sensible prioritization axis,
not a strong causal sieve on its own. The pipeline's power comes from
*combining* it with gene, disease, and brain-activity evidence.

---

## Interpretation & caveats

Read `top_candidates_interpretation.md` for the top-candidate biology. Three
caveats apply throughout and are load-bearing:

1. **Overlap ≠ causation.** "Overlaps a GWAS locus" means within 25 kb of a
   lead SNP, not that the HAR is the causal element or that its
   human-specific changes drive the association.
2. **Nearest gene ≠ target gene.** `nearest_tss` assignments are a proximity
   heuristic; `plac_linked` assignments rest on a neuronal PLAC-seq interaction (stronger,
   still correlative).
3. **Acceleration is real but not lineage-polarized.** Each HAR's human (hg38)
   and chimpanzee (panTro5) orthologous sequences are fetched from the UCSC
   sequence API (coordinates from Cui Supplemental Table 2), globally aligned,
   and the substitution rate (subs / aligned bp) drives the axis. The caveat:
   human–chimp divergence does not by itself prove the change occurred on the
   *human* branch rather than the chimp branch; strict human-specific
   acceleration needs an outgroup (e.g. macaque) or a branch model. It is a
   first-order measure, and the axis weight (0.07) reflects that.
4. **Motif disruption is a model-based call.** The motif axis counts JASPAR
   TF-binding sites gained/lost between the alleles at a fixed false-positive
   threshold (1e-4). This flags *candidate* regulatory consequences; it does not
   quantify affinity change, and JASPAR PWMs are themselves models of binding
   preference. Treated as a low-weight (0.05) hypothesis-generating signal.

**Antagonistic pleiotropy.** HARs were deeply conserved across mammals, then
changed rapidly on the human lineage. When such an element sits in the
regulatory neighbourhood of a gene whose disruption causes a developmental
disorder *and* whose common variants associate with a psychiatric/cognitive
trait, the same regulatory tuning that may have been advantageous for human
brain evolution can raise disease liability under a different genetic
background, a hypothesis-generating pattern, not a mechanistic claim.

---

## How this was built with Claude Science

This project was developed end-to-end with **[Claude Science](https://www.anthropic.com)**,
Anthropic's agent for scientific computing. The same glass-box principle that
governs the pipeline governs how it was built: every step is inspectable, and
the agent showed its work. Concretely, Claude Science:

- **Wrote and iterated the pipeline modules** — the funnel filters, the seven
  evidence axes, and the transparent additive score in `score.py`, each kept
  small and legible so the reasoning stays visible.
- **Handled the 9.6 GB problem without downloading 9.6 GB.** The 241-way phyloP
  conservation track is far too large to pull down. Instead of fetching it,
  the agent queried the bigWig *remotely* — reading only the ~200 bases under
  each of the ~3,000 HARs via `pyBigWig` interval stats. The file never lands
  on disk (`filters.annotate_phylop`).
- **Fact-checked the candidates against the real tables.** Rather than trusting
  the narrative, the agent loaded the scored parquet and verified the top hits
  axis by axis — which is how the #1 element near *ZSWIM6* was correctly
  attributed to conservation + brain activity (not gene link), and *RPS23* was
  confirmed as its mirror image (strong gene link, weak constraint).
- **Computed the funnel comparison and enrichment.** The three-funnel
  reshuffle (anchored 363 ⊂ discovery 577 ⊂ relaxed 2,757) and the
  constrained-vs-unconstrained GWAS enrichment (1.37×, Fisher p = 3.6e-3) were
  both computed directly from the candidate tables.
- **Re-ran the whole pipeline byte-for-byte.** A clean re-run reproduced the
  identical funnel (3,257 → 2,757 → 1,718 → 363), identical rank order, and a
  maximum `total_score` difference of 0.0 — confirming the reproducibility the
  `manifest.csv` spine is designed for.
- **Generated the figures** in this repository and the accompanying deck.

*Provenance note:* the pipeline is a collaboration — scientific direction,
dataset choices, and the biological framing are the author's; Claude Science
did the implementation, verification, and figure work described above. Every
result is reproducible from source via `python run_pipeline.py`.

## License

MIT. See `LICENSE`.

## Citations

If you use this pipeline, please cite the primary HAR source and the dataset(s)
whose evidence axis you rely on. Full download URLs, access dates, and checksums
are in `data/manifest.csv`; expanded notes are in *Sources & provenance* above.

**Primary HAR set & HAR→gene map**
- Cui et al. (2025). "Comparative characterization of human accelerated regions
  in neurons." *Nature* 640:991–999. doi:[10.1038/s41586-025-08622-x](https://doi.org/10.1038/s41586-025-08622-x).
  *(3,257 HAR coordinates + neuronal PLAC-seq HAR→gene interaction map.)*

**Neurodevelopmental gene set — DDG2P / Gene2Phenotype**
- Thormann et al. (2024). "Curating genomic disease-gene relationships with
  Gene2Phenotype (G2P)." *Genome Medicine*. doi:[10.1186/s13073-024-01398-1](https://doi.org/10.1186/s13073-024-01398-1).
- Thormann et al. (2019). *Nature Communications* 10:2373. doi:[10.1038/s41467-019-10016-3](https://doi.org/10.1038/s41467-019-10016-3).

**Neuropsychiatric GWAS — NHGRI-EBI GWAS Catalog**
- Cerezo et al. (2025). *Nucleic Acids Research* 53(D1):D998–D1005. doi:[10.1093/nar/gkae1070](https://doi.org/10.1093/nar/gkae1070).
- Sollis et al. (2023). *Nucleic Acids Research* 51(D1):D977–D985. doi:[10.1093/nar/gkac1010](https://doi.org/10.1093/nar/gkac1010).

**Mammalian constraint — Zoonomia 241-way phyloP**
- Christmas et al. (2023). "Evolutionary constraint and innovation across
  hundreds of placental mammals." *Science* 380:eabn3943. doi:[10.1126/science.abn3943](https://doi.org/10.1126/science.abn3943).
- Sullivan et al. (2023). *Science* 380:eabn2937. doi:[10.1126/science.abn2937](https://doi.org/10.1126/science.abn2937). *(constraint → disease-mapping utility.)*

**Developing-brain open chromatin — ENCODE embryonic-brain DNase-seq**
- Davis et al. (2018). "The Encyclopedia of DNA Elements (ENCODE): data portal
  update." *Nucleic Acids Research*. doi:[10.1093/nar/gkx1081](https://doi.org/10.1093/nar/gkx1081).
- The ENCODE Project Consortium (2012). *Nature* 489:57–74. doi:[10.1038/nature11247](https://doi.org/10.1038/nature11247).
  *(File ENCFF660HML, experiment ENCSR420RWU.)*

**Developmental transcriptome — BrainSpan (Allen Institute)**
- Miller et al. (2014). "Transcriptional landscape of the prenatal human brain."
  *Nature* 508:199–206. doi:[10.1038/nature13185](https://doi.org/10.1038/nature13185).

**TF motifs — JASPAR2024 CORE vertebrates**
- Rauluseviciute et al. (2024). "JASPAR 2024: 20th anniversary of the
  open-access database of transcription factor binding profiles." *Nucleic Acids
  Research* 52(D1):D174–D182. doi:[10.1093/nar/gkad1059](https://doi.org/10.1093/nar/gkad1059).

**Genome assembly, gene coordinates & ortholog sequences — UCSC Genome Browser**
- Kent et al. (2002). "The Human Genome Browser at UCSC." *Genome Research*
  12:996–1006. doi:[10.1101/gr.229102](https://doi.org/10.1101/gr.229102).
  *(refGene hg38 gene models; hg38 + panTro5 ortholog sequence API.)*
