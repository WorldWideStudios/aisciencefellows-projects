# Key questions — DMD mechanism-mapping

Source: rare-disease platform deck (Q2 2026). The deck's target gene was
ALMS1 (Alström syndrome); questions below are transcribed with gene / disease
terms swapped for DMD context (**gene = DMD**, **protein = dystrophin**,
**disease = DMD / BMD**). Structure and phrasing otherwise preserved.

The deck frames the problem in four pillars:

> Mechanism-mapping problem: starting from a rare disease gene with many known
> pathogenic variants, we want to infer:
>
> 1. What has been published about the variant in the rare disease literature?
> 2. What happens to the transcript?
> 3. What happens to the DMD protein (dystrophin)?
> 4. What happens downstream of dystrophin?
>
> **Ultimate goal:** How do these intermediate findings (mechanisms) explain
> the connection between DMD pathogenic variants and clinical phenotypes
> (DMD / BMD signs and symptoms)?

These are the questions the workbench's **Explore Data** tab must be able to
answer, chart-first, one question at a time.

---

## Pillar 1 — Literature about the variants

**Rough instructions**
- Scrape DMD papers to find all DMD-pathogenic variants and the information
  published about each (e.g. exon #).
- Search variant annotations (missense, nonsense, frameshift, splice,
  synonymous).

**Deliverables**
- A list of information published about the variants (e.g. exon #).
- A table where each variant is a row and each column is a variable about the
  variant (e.g. annotation, exon #). Include the paper each variant was
  published in.

---

## Pillar 2 — What happens to the transcript?

For each variant, what happens to the transcript?

- NMD?
- Aberrant splicing?
- Altered expression?
- Allele-specific expression?

### 2a. NMD escape vs trigger

**Rough instructions**
- Determine which pathogenic variants generate premature termination codons
  (PTCs).
- Run PTC-generating variants through the **aenmd** R package. Separate
  variants into *loss of transcript* vs *stable transcript*.

**Deliverables**
- Table + figure communicating how many variants are predicted to generate
  PTCs, and of those, how many are predicted to be NMD-triggering vs
  NMD-escaping.

**Clinical tie-in (statistical)**
1. Is there a statistically significant relationship between a variant's NMD
   status and individual symptoms? E.g. are DMD individuals with loss-of-
   transcript variants more likely to report cardio symptoms?
2. Is there a statistically significant relationship between NMD status and
   syndromic score, after controlling for age? E.g. are DMD individuals with
   loss-of-transcript variants more likely to report more symptoms?

### 2b. Where DMD is expressed (single-cell + bulk)

**Rough instructions**
- Query DMD in GTEx single-cell portal (raw data, not visuals).
- Rank cell types by (i) % cells with DMD expression, (ii) median DMD
  expression per cell.
- Statistical analysis on the correlation between rank-of-detection and
  rank-of-median-expression.

**Deliverables**
- Table ranking cell types by % cells with DMD expression.
- Table ranking cell types by median DMD expression.
- Correlation of the two rankings.

**Clinical tie-in (statistical)**
1. Gut-check: do the cell-type rankings make sense given cells / tissues most
   highly impacted by DMD? (skeletal muscle, cardiac muscle, diaphragm,
   Purkinje neurons for cognitive symptoms, etc.)
2. Repeat with bulk GTEx (DMD expression across tissue types).

### 2c. Isoform / splice

Sample questions:

- Highest-expression tissues per isoform?
- Disease-relevant tissue for each isoform?
- Isoform usage?
- Splice variation?

Also: run pathogenic variants through **AbSplice** to predict exon-skipping.

---

## Pillar 3 — What happens to dystrophin (the protein)?

For each variant, what happens to dystrophin?

- Reduced abundance?
- Misfolding?
- ER retention?
- Degradation?
- Altered interactions?

### 3a. Predicted structure (ESMFold-2)

**Rough instructions**
- Obtain the AA sequence of wild-type dystrophin.
- Generate AA sequences of dystrophin with pathogenic variants.
- Run all sequences in ESMFold-2.

**Deliverables**
- Protein figures + TMScore (confidence score) from ESMFold-2.

### 3b. Highly-constrained residues (ESM2 LLR)

**Rough instructions**
- Run WT and variant dystrophin sequences through **ESM2** to obtain
  log-likelihood ratios (LLR) at the variant position.

**Deliverables**
- Figure of LLRs across the wild-type dystrophin sequence.
- Table of LLRs at each DMD individual's variant position.

**Clinical tie-in (statistical)**
1. Is there a statistically significant relationship between a variant's LLR
   and individual symptoms, after controlling for age? E.g. are DMD
   individuals with "more severe" variants more likely to report cardio
   symptoms?
2. Is there a statistically significant relationship between LLR and
   syndromic score, after controlling for age? E.g. are DMD individuals with
   more severe variants more likely to report more symptoms?

### 3c. Synthesis discussion

1. How can we use prior findings (annotation / NMD / GTEx / protein data) to
   make inferences about dystrophin abundance in DMD individuals?
2. Is it possible to use UK Biobank or other proteomics data to repeat the
   healthy-individuals expression comparison (the GTEx analysis from Pillar
   2)?

---

## Pillar 4 — What happens downstream of dystrophin?

Possible next steps for evaluating downstream effects of dystrophin loss:

- **Open Targets** — pull molecular interactors and pathways for DMD.
- **ARCHS4** — pull co-expression networks to generate top correlated genes,
  modules, pathway enrichments, potential downstream pathways.
- **STRING** — pull protein interaction network to evaluate protein
  complexes, direct interactors, pathway neighbors.
- **Geneformer** — simulate perturbation to predict cellular response.
- **Connectivity Map (CMap)** — transcription matching / possibility of
  rescuing the DMD-loss signature.

---

## Ultimate synthesis

How do the intermediate findings (mechanisms) explain the connection between
DMD pathogenic variants and clinical phenotypes (DMD / BMD signs and
symptoms)?

This is the question **Explore Mechanism** answers: overview (mechanism
filters) → focus (hypothesis list sorted by Pareto score) → detail (chain
diagram + supporting premises for one hypothesis).
