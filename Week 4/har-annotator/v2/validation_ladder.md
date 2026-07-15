# Wet-lab validation ladder

*From computational candidate to causal proof.*

The HAR-annotator pipeline ends where the biology begins: it produces a ranked,
source-traceable shortlist, but a high score is a **hypothesis**, not a result.
This document lays out the experimental path that would test the top candidates,
organized as a ladder — each rung answers a sharper question at higher cost and
lower throughput, and only elements that pass one rung climb to the next.

The design principle mirrors the pipeline itself: **start broad and cheap, narrow
as certainty rises.** Tier 1 screens hundreds of elements for *any* regulatory
activity; Tier 3 commits a year to a single element's developmental consequence.

---

## Tier 0 — in silico (complete)

**Question:** Which HARs are most likely to be human-specific brain-development
regulators?

- 3,257 HARs → **363** disease-anchored shortlist (or **577** in discovery mode)
- Scored on 7 transparent axes; every score traces to a public dataset
- Top hit: an element Hi-C-looping to **ZSWIM6** (chr5); POC1B and TCF20 close behind
- **Cost:** $0 · **Time:** minutes · **Throughput:** all HARs

**Output that feeds Tier 1:** the ranked candidate list with genomic coordinates,
the human and chimp (panTro5) ortholog sequences already fetched for each element,
and the predicted target gene for each.

---

## Tier 1 — Massively Parallel Reporter Assay (MPRA)

**Question:** Does the element drive transcription, and does the *human* allele
behave differently from the *chimp* allele?

**Design.** Synthesize both the human and the chimp ortholog of the top ~200
elements (the sequences are already in `data/har_ortholog_seqs*.parquet`). Clone
each upstream of a minimal promoter driving a barcoded reporter, so that each
allele carries a unique set of barcodes. Pool, transfect into a fetal-brain-like
context — neural progenitor cells (NPCs) or organoid-derived neural cells — and
sequence the transcribed barcodes.

**Readout.** RNA-barcode / DNA-barcode ratio = regulatory activity per allele.
The human-vs-chimp activity difference is the quantity of interest: it directly
tests whether the human-specific substitutions changed enhancer strength.

**Decision rule.** Advance elements with (a) activity significantly above the
scrambled-sequence null and (b) a significant human-vs-chimp allelic difference.

- **Cost:** ~$15k · **Time:** 2-3 months · **Throughput:** hundreds in parallel
- **Prior art:** HAR MPRAs (Uebbing et al. 2021 PNAS; Whalen/Pollard) show this
  is tractable at exactly this scale.

---

## Tier 2 — Capture-C + CRISPR interference (CRISPRi)

**Question:** *Which* gene does the element control, and is the element *necessary*
for that gene's expression?

**Design, part A (Capture-C).** For each element that passed Tier 1, run Capture-C
using the HAR as the viewpoint. This tests the physical chromatin loop that the
pipeline *predicted* from published PLAC-seq/Hi-C — here it is measured directly in
the relevant cell type, confirming (or refuting) the HAR→target-gene assignment.

**Design, part B (CRISPRi).** Tile dCas9-KRAB guide RNAs across the element in NPCs
to silence it, then measure the predicted target gene by RT-qPCR / RNA-seq. A drop
in target-gene expression on silencing is direct evidence that the element is a
*necessary* activating regulator in this context.

**Readout.** 3D contact frequency (Capture-C) + target-gene knockdown effect size
(CRISPRi).

**Decision rule.** Advance elements where the loop is confirmed *and* silencing
produces a reproducible knockdown of the predicted gene.

- **Cost:** ~$40k · **Time:** 4-6 months · **Throughput:** ~10 elements

---

## Tier 3 — Humanized cortical organoids

**Question:** Does swapping the human allele for the chimp allele (or vice versa)
change how the brain develops?

**Design.** Using an isogenic strategy, knock the human allele into a chimpanzee
iPSC line (or the chimp allele into a human line) so the *only* difference between
the paired lines is the element's sequence. Differentiate both into cortical
organoids and profile them across the mid-fetal convergence window with single-cell
RNA-seq plus morphometry.

**Readout.** Cell-type proportions, neurogenic timing (e.g. progenitor→neuron
transition rate), and the target gene's expression trajectory — compared between
the human-allele and chimp-allele isogenic pair.

**Decision rule.** A reproducible, allele-dependent shift in a developmental
phenotype is the strongest available evidence that the element contributed to
human-specific brain development.

- **Cost:** ~$150k · **Time:** 12-18 months · **Throughput:** 1-3 elements
- **Prior art:** humanized-allele organoid comparisons are established for a
  handful of human-specific loci; this applies the same design to a HAR the
  pipeline nominated.

---

## Why this ordering

1. **Cheap filters first.** Tier 1 costs ~1% of Tier 3 per element and runs
   hundreds in parallel — so most elements are triaged before any expensive work.
2. **Each rung answers a different question.** Activity (T1) → target + necessity
   (T2) → developmental consequence (T3). Passing all three converts a computed
   score into a causal claim.
3. **The pipeline's predictions are testable at every rung.** The HAR→gene loop
   (Capture-C), the human-vs-chimp difference (MPRA allelic contrast), and the
   developmental window (organoid time-course) each map to a specific pipeline
   axis, so the wet-lab work also validates the *scoring model*, not just the hits.

*Cost and time figures are order-of-magnitude planning estimates for a standard
academic core-facility setting, not quotes.*
