# Top HAR Candidates — Interpretation

*Human Accelerated Region (HAR) annotator — Phase 4.*
*Source HAR set: Cui et al. 2025, Nature (3,257 HARs, hg38). Candidate set: 363 HARs passing constraint → neurodev-gene proximity → neuropsychiatric-GWAS overlap. Ranked by the transparent additive evidence score (Phase 3).*

---

## How to read this document

Each candidate below is a **regulatory** element, not a gene. A HAR earns its
rank by combining seven independent lines of evidence (mammalian constraint,
human–chimp acceleration, neurodevelopmental-gene link, neuropsychiatric-GWAS
overlap, developing-brain regulatory activity — *where* — the developmental
timing of the target gene — *when* — and TF-motif disruption). The score is
fully decomposable — every candidate's `contrib_*` columns in
`har_shortlist_ranked.csv` show exactly which axes drove its rank.

**Ranks reflect the seven-axis default (temporal included).** Adding the
developmental-timing axis re-normalized the weights and re-ranked the list
relative to the pre-temporal v1 shortlist; running `run_pipeline.py
--no-temporal` reproduces the six-axis ordering exactly. All ranks and scores
below are the seven-axis values.

**Five caveats apply to every entry and are not repeated each time:**

1. **Overlap is not causation.** "Overlaps a neuropsychiatric GWAS locus"
   means the HAR falls within 25 kb of a genome-wide-significant lead SNP for
   a neuropsychiatric/cognitive trait. It does **not** establish that the HAR
   is the causal element at that locus, nor that its human-specific changes
   drive the association. LD structure means the true causal variant may lie
   elsewhere in the block.
2. **Nearest gene ≠ target gene.** Where the assignment method is
   `nearest_tss`, the linked gene is simply the closest transcription start
   site — a heuristic. Where it is `plac_linked`, a neuronal PLAC-seq interaction (Cui
   2025) physically connects the HAR to that gene's promoter, which is
   stronger but still correlative.
3. **Acceleration is a real substitution rate, but not lineage-polarized.**
   Each HAR's human (hg38) and chimp (panTro5) orthologous sequences are
   fetched, aligned, and the substitution rate (subs / aligned bp) drives the
   axis — replacing the earlier HAR-width proxy. The caveat that remains:
   human–chimp divergence does not by itself prove the change happened on the
   *human* branch (that needs an outgroup such as macaque). Where a candidate's
   rank is driven by this axis, the entry says so explicitly.
4. **Temporal timing is gene-level, not element-level.** The `when` axis scores
   the *target gene's* prenatal expression trajectory (BrainSpan), not the HAR
   itself: it asks what fraction of the gene's prenatal expression falls in the
   mid-fetal convergence window (~10–24 pcw). A high temporal score means the
   linked gene is most active in the developmental moment where human-specific
   regulation and neuropsychiatric risk are thought to converge — it does not
   demonstrate that the HAR drives that timing. Genes absent from BrainSpan
   (or with no prenatal signal) score 0 on this axis.
5. **Motif disruption is a presence/absence model call.** The `motif` axis
   counts JASPAR TF-binding sites gained or lost between the human and chimp
   alleles (879 PWMs, false-positive rate 1e-4). It flags *candidate* regulatory
   consequences of the human-specific changes; it does not measure affinity
   change, and the PWMs are themselves models. Low weight (0.05) by design.

**Antagonistic-pleiotropy framing.** HARs are, by definition, sequences that
were deeply conserved across mammals (strong purifying selection) and then
changed rapidly on the human lineage. When such an element sits in the
regulatory neighbourhood of a gene whose disruption causes a developmental
disorder *and* whose common variants associate with a psychiatric/cognitive
trait, it fits an antagonistic-pleiotropy pattern: the same regulatory tuning
that may have been advantageous for human brain evolution can, at the tails of
its expression distribution or under a different genetic background, raise
disease liability. This is a hypothesis-generating observation, not a
mechanistic claim.

---

## Tier 1 — highest combined evidence

### HAR_2378 → *ZSWIM6* (rank 1, score 0.618)
Now the **top candidate**, promoted from rank 4 by the real acceleration axis:
this element has the **highest human–chimp substitution rate of any candidate**
(subst_rate 0.46; acceleration score 0.975), i.e. it is genuinely among the
most-diverged HARs in the set — exactly what the width proxy failed to capture.
It also carries the highest constraint among the leaders (phyloP 6.35), is
PLAC-seq-linked to *ZSWIM6* (strong), is embryonic-brain active, overlaps
*educational attainment*, and has 63% mid-fetal expression (temporal score
0.63, peak 9 pcw). *ZSWIM6* variants cause acromelic frontonasal dysostosis
with neurodevelopmental features and have been recurrently implicated in
schizophrenia GWAS — a strong antagonistic-pleiotropy candidate whose real
divergence now reinforces the case.

### HAR_575 → *POC1B* (rank 2, score 0.605)
PLAC-seq-linked to *POC1B* (DDG2P **definitive**), overlaps an *educational
attainment* GWAS signal (p = 9×10⁻²⁴, the strongest disease signal in the top
tier), lands in an embryonic-brain DNase peak, and is well constrained
(phyloP mean 4.55). It scores in the top band on gene link, disease overlap
**and** brain activity simultaneously — which is why it stays near the top
despite only moderate constraint, a low substitution rate (acceleration
score 0.04), and a target-gene expression peak (9 pcw) just *outside* the
mid-fetal window (temporal score 0.34). *POC1B* encodes a centriolar protein;
its developmental-disorder link is through ciliopathy/retinal-dystrophy
phenotypes rather than a classic cortical-patterning role, so the
neuropsychiatric interpretation should be treated cautiously — the
educational-attainment overlap may reflect a neighbouring gene in the same TAD.

### HAR_1826 → *TCF20* (rank 3, score 0.605)
PLAC-seq-linked to *TCF20* (definitive), high constraint (phyloP 5.86), brain-
active, overlaps a *cognitive performance* locus. The temporal axis keeps it
near the top: *TCF20* peaks at 13 pcw with 68% of its prenatal expression
**inside** the mid-fetal window (temporal score 0.68), so the *where* and
*when* axes reinforce each other. *TCF20* haploinsufficiency causes an
autism/intellectual-disability syndrome — a clean concordance between the
rare-disease gene and the common-variant trait. A compact, low-divergence
element (acceleration score 0.04); it ranks on gene + constraint + timing.

### HAR_2635 → *FBXL4* (rank 4, score 0.548)
PLAC-seq-linked to *FBXL4* (definitive), brain-active, overlaps an *educational
attainment* locus, phyloP mean 4.61, with the highest motif-disruption score in
the top tier (10 TF sites gained/lost). *FBXL4* peaks at 9 pcw with 54%
mid-fetal expression (temporal score 0.54, just outside the window). Its
substitution rate is low (acceleration score 0.01) — the earlier proxy ranked
it 3rd largely because it is the widest element (1,871 bp), a boost the real
divergence measure removes. *FBXL4* encephalomyopathic mitochondrial DNA-
depletion syndrome is an early-onset neurodevelopmental disorder, so the rare-
disease direction is well supported; the common-variant overlap carries the
usual overlap-not-causation caveat. (A second HAR near *FBXL4*, HAR_2634,
ranks 6 by nearest-TSS — a HAR-dense locus.)

### HAR_1613 → *HOXD13* / (PLAC-seq: *LNPK*) (rank 7, score 0.525)
Nearest neurodev gene is *HOXD13* (definitive) but the neuronal PLAC-seq
interaction points to *LNPK*. High constraint (phyloP 5.54), active in
embryonic brain, overlaps a *major depressive disorder* locus, but low
substitution rate (acceleration score 0.01). It carries a temporal score of 0
(neither the nearest nor the linked locus produced a usable prenatal
trajectory), which is why it sits just below the timed candidates. The
gene-assignment ambiguity here is the entire point of the nearest-vs-PLAC-seq
distinction: the developmental-disorder gene (*HOXD13*, limb/axial patterning)
and the physically-contacted gene (*LNPK*, a reticulon-family ER-shaping
protein linked to a recessive neurodevelopmental syndrome) are different
biological stories. Reported as-is; not resolved.

---

## Tier 2 — classic neurodevelopmental / evolutionary genes

These are the elements a domain expert would expect to see, and their presence
is a sanity check on the pipeline.

### HAR_1545 → *ZEB2* (rank 5, score 0.538)
Nearest-TSS to *ZEB2* (definitive), very high constraint (phyloP 6.23), and
the **strongest disease overlap of any candidate** — an *educational
attainment* signal at p = 2×10⁻³¹. The temporal axis reinforces it: *ZEB2*
peaks at 13 pcw with 73% mid-fetal expression (temporal score 0.73, inside the
window), holding it at rank 5. *ZEB2* (Mowat-Wilson
syndrome) is a master transcription factor for cortical interneuron and
oligodendrocyte development. Nine separate HARs sit near *ZEB2* in the
candidate set, consistent with a HAR-dense regulatory landscape around a
dosage-sensitive neurodevelopmental TF.

### HAR_2153 → *PHOX2B* (rank 40, score 0.434)
Nearest-TSS to *PHOX2B* (definitive), phyloP 5.57, wide element (729 bp),
brain-active, overlaps *personality/cognitive* trait signals, moderate motif
disruption (19 sites). It falls to rank 40 under the temporal default because
*PHOX2B* has almost no prenatal
expression in the mid-fetal window (peak 8 pcw, temporal score 0.01) — a clear
illustration of the *when* axis down-weighting a gene whose developmental
program runs earlier and in the autonomic rather than cortical lineage.
*PHOX2B* is the master regulator of autonomic-nervous-system neuron identity
(mutated in congenital central hypoventilation syndrome); its appearance
illustrates that "neurodevelopmental" in this pipeline spans autonomic as well
as cortical programs.

### HAR_1308 → *TCF4* (rank 19, score 0.487)
Nearest-TSS to *TCF4* (definitive), overlaps *educational attainment* at
p = 9×10⁻¹⁷, with 62% mid-fetal expression (temporal score 0.62, peak 9 pcw).
*TCF4* is one of the best-established antagonistic-pleiotropy
genes in psychiatry: <cite index="14-1,14-3">common variants in and around TCF4 are associated with increased schizophrenia risk, while rare damaging TCF4 mutations cause Pitt–Hopkins syndrome and have been found in intellectual disability and autism spectrum disorder</cite>. <cite index="10-1">It is a basic helix-loop-helix transcription factor essential for neurocognitive development.</cite> The dual rare-disease / common-trait architecture is exactly the pattern the disease axis is designed to surface. Constraint here is only moderate (phyloP 2.81), so this candidate rides on gene confidence + brain activity rather than sequence conservation.

### HAR_2395 → *MEF2C* (rank 10, score 0.508)
Nearest-TSS to *MEF2C* (definitive), overlaps an *Alzheimer disease /
educational attainment* locus, and is now lifted by **two** context axes: it
has the highest mid-fetal fraction of any candidate discussed here — 81% of its
prenatal expression falls in the window, peaking exactly at 24 pcw (temporal
score 0.81) — **and** a high real substitution rate (acceleration score 0.78),
placing it among the genuinely diverged elements. *MEF2C* is a synaptic-
activity-dependent transcription factor central to excitatory-neuron
development and a recurrent intellectual-disability gene; five HARs flank it in
the candidate set.

### HAR_2828 → *FOXP2* (rank 57, score 0.417)
PLAC-seq-linked to *FOXP2* (strong). *FOXP2* is the canonical human-evolution
speech-and-language gene, and its locus is independently one of the most
HAR-enriched, fastest-accelerating noncoding regions in the genome: <cite index="1-6">the topologically associating domain containing the FOXP2 locus includes two clusters of 12 HARs, placing it among the top regions showing fast acceleration rates in the human genome</cite>, and <cite index="1-7">at least five FOXP2-HARs behave as transcriptional enhancers across developmental stages</cite>. Six *FOXP2*-neighbouring HARs appear in our candidate set. Note this element does **not** overlap an embryonic DNase peak in the single ENCODE sample used (brain axis = 0) despite a solid temporal score (0.62, peak 9 pcw), which caps its rank — a reminder that a single-tissue, single-timepoint accessibility track under-calls genuinely active enhancers.

### HAR_526 → *SOX5* (rank 20, score 0.486)
PLAC-seq-linked to *SOX5* (strong), overlaps *educational attainment*, with 70%
mid-fetal expression (temporal score 0.70, peak 12 pcw). This candidate is the
clearest example of the acceleration upgrade changing a rank: it has the second-
highest substitution rate among the genes discussed here (acceleration score
0.95) and climbs from rank 41 (proxy) to rank 20, even though it still lacks an
embryonic DNase peak in the single ENCODE sample (brain axis = 0). The real
divergence measure surfaces a genuinely fast-evolving element the width proxy
had buried. *SOX5* controls the sequential
generation and migration of deep-layer cortical projection neurons; Lamb-
Shaffer syndrome results from its disruption. Six *SOX5*-linked HARs are
present in the candidate set.

---

## What the ranking is *not* telling you

- **Rank order is weight-dependent.** The seven weights (constraint 0.18, gene
  0.22, disease 0.22, brain 0.13, temporal 0.13, acceleration 0.07, motif 0.05)
  are a defensible default, not ground truth. `score.py` exposes them as a
  parameter; re-running with different weights — or with `--no-temporal` to
  drop back to the six-axis scheme — will reshuffle the middle of the list. The
  top ~5 are robust because they score highly on several axes at once.
- **Absence from the top is not evidence against a gene.** *FOXP2* (rank 57)
  and *RBFOX1* rank well down the list largely because the single embryonic
  DNase track and the GWAS proximity filter penalise them, not because they are
  weak candidates. The full 363-row table should be read alongside the rank.
- **The disease axis is intentionally conservative.** Educational-attainment
  and cognitive-function GWAS dominate simply because those are the
  best-powered studies in the catalog; this is an ascertainment feature of
  GWAS, not a biological statement that these HARs are "about" education.

---

*Literature accessed via web search (OpenAlex/PubMed API was unreachable from
the sandbox this session). Citations above point to primary sources for the
FOXP2 and TCF4 claims; disease-gene roles for the remaining candidates are
drawn from their DDG2P developmental-disorder annotations (definitive/strong
tiers) recorded in the evidence table.*
