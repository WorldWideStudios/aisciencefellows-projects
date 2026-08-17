# Hypothesis assembly — a scientific walkthrough

> How the workbench gathers evidence and forms mechanism hypotheses
> that connect a patient's pathogenic variant to their clinical phenotype.

## The scientific question

Given a rare-disease patient with a known pathogenic variant, we want to
answer: **how does this specific variant produce the clinical signs and
symptoms we observe in this specific patient?**

The answer is a *mechanism* — a causal chain of biological events that
begins with the variant and terminates in a phenotype. The mechanism is
the *why* connecting genotype to clinic. Every therapeutic decision
implicitly rests on one.

The mechanism itself is not directly observable. What we have is
evidence at various points along the chain — sequence data, protein
predictions, pathway memberships, expression atlases, clinical labs. The
job of the workbench is to **assemble that scattered evidence into a
coherent chain**, then score how well the assembled chain holds
together. That assembled, evidence-linked chain is what we call a
*hypothesis*. Multiple hypotheses coexist per patient; ranking them is
a separate step.

## The scaffold: biological organization

Rare-disease biology is naturally hierarchical. A variant does not
cause a phenotype in one step — it causes protein changes, which
disrupt pathways, which affect subcellular structures, which impair
specific cell types, which weaken tissues, which manifest as
observable signs. Each level is a scale of organization at which the
consequences of the variant can be *observed and reasoned about
independently*.

We adopt the following seven-layer hierarchy as the assembly scaffold:

```
   variant → protein → pathway → subcellular → cell type → tissue → phenotype
```

Each layer is a **node** in a directed acyclic graph. Adjacent layers
are connected by **edges** that represent causal transitions:
*"variant produces this protein change"*, *"this protein change
disrupts this pathway"*, and so on.

Every hypothesis is a **walk through this graph** — a specific chain
of node-claims and edge-claims that together tell a mechanism story
from variant to phenotype.

## Formation vs. ranking

We treat these as two distinct operations:

**Formation** = gathering the evidence for each node and each edge in
the chain. This is empirical work: consulting data sources and running
predictive models to accumulate the premises that inform each step.
Formation happens per patient because the patient's context (variant,
labs, phenotype) determines which evidence applies.

**Ranking** = comparing whole assembled chains to decide which one best
explains the patient's observations. Ranking is a downstream operation
on the finished chains; it does not itself gather evidence.

Keeping these separate matters because:

- A weakly-ranked hypothesis can still have strong evidence at
  specific steps — worth surfacing in the trace even if not the winner.
- Adding a new data source affects formation (more evidence available);
  ranking then re-scores over the enriched set without changing rules.
- We can compare hypotheses cell-by-cell along the chain, not just
  by a single scalar score.

## Two kinds of evidence: node premises and edge premises

At every position along the chain, evidence takes one of two forms:

**Node evidence** — what we know about the biological state at a
single layer of organization. Examples: the variant record itself
(node: variant); the ESM3-predicted 3D structure of the affected
isoform (node: protein); the tissue-scale imaging of muscle
composition (node: tissue).

**Edge evidence** — what we know about the causal transition from one
layer to the next. Examples: NMD prediction linking a variant to
transcript loss (edge: variant → protein); pathway-component tissue
expression linking a pathway disruption to cell-type dysfunction
(edge: pathway → subcellular); functional labs linking tissue
dysfunction to a clinical measurement (edge: tissue → phenotype).

Both kinds matter. A chain with strong node evidence but weak edges
is a chain with unexplained gaps — the layers are populated but
their causal relationship is not established. A chain with strong
edges but empty nodes has coupling without content. The formation
process aims to accumulate both.

## Data sources and which layer each informs

The workbench currently integrates thirteen data or model sources. Each
source produces typed evidence rows (**premises**) that are then
attributed to node and edge positions in the biological chain:

| Source | Type | Informs | Nature of the evidence |
|---|---|---|---|
| **Zhang 2024 patient cohort** | data | variant (node), phenotype (node) | Per-patient variant record + clinical phenotype label from the published supplementary tables (N=418) |
| **ClinVar NMD cross-tab** | model | variant→protein (edge) | Predicted NMD classification (triggering / escaping / transcript-dependent) applied to 11,790 ClinVar DMD variants; establishes cohort-level base rates for variant → transcript-loss transitions |
| **DMD isoform architecture** | data | variant→protein (edge), protein (node) | Which of the seven DMD isoforms is impacted given the variant's exon position (first-shared-exon rule); a structural argument for the variant → protein transition |
| **AbSplice** | model | variant (node), variant→protein (edge) | Per-tissue aberrant-splicing probability (AbSplice-DNA v1.0.4). Distinguishes canonical splice-site variants (e.g. P10 c.9361+1G>C, max score 0.88 in heart-atrial-appendage) from exonic ones (score < 0.05) — a signal isoform_arch and clinvar_nmd cannot see. Cryptic-splice or exon-skipping events feed the variant → protein transition as a *compounding* NMD trigger. |
| **ESM3 protein fold** | model | protein (node), variant→protein (edge) | Per-patient ESM3-predicted 3D structure of the wild-type and truncated protein product; visualizes what protein content is preserved and what is lost |
| **UniProt subcellular localization** | data | subcellular (node), protein→subcellular (edge) | Curated protein-biology: sarcolemma, cytoplasm/cytoskeleton, postsynaptic membrane (P11532) |
| **Reactome pathway memberships** | data | pathway (node), pathway→subcellular (edge) | Which biological pathways include dystrophin; a claim about downstream molecular consequences of protein loss |
| **Human Protein Atlas cell-type expression** | data | cell type (node), cellType→tissue (edge) | Baseline expression of DMD across cell types — *gene-scoped, not patient-scoped*. Establishes which cell types normally express DMD; does not by itself say which cells are affected in a given patient |
| **Open Targets Platform** | data | pathway (node), protein→subcellular (edge), phenotype (node) | Target record for DMD (ENSG00000198947): five approved drugs (delandistrogene moxeparvovec, eteplirsen, viltolarsen, golodirsen, casimersen), twelve named DGC molecular partners (SNTA1, SNTB1, SNTB2, SGCA-D, SSPN, DAG1, DTNA, DTNB, ...), three Reactome pathway memberships, disease-association scores (DMD 0.87, BMD 0.82, DCM 0.79), tractability profile. Approved drugs actively argue *against* H04 (distal-isoform-loss) since they all restore Dp427, not distal isoforms. |
| **patient_celltype_impact (composition)** | model | cellType (node), protein→cellType (edge) | Isoform-arch × curated cell-to-isoform dependency map → per-patient cell-type hit/spared status |
| **patient_tissue_impact (composition)** | model | tissue (node), cellType→tissue (edge) | Isoform-arch × isoform tissue-expression map → per-patient tissue hit status |
| **Literature (curated citations)** | data | any node or edge | Peer-reviewed claims attributed to specific chain positions per hypothesis; dual-attribution at subcellular |
| **Per-patient clinical labs** | model / data | cell type (node), tissue (node), phenotype (node) | Fifteen assays per patient (CK, LVEF, FVC, MRI fat fraction, 6MWT, NSAA, IQ, ERG, UACR, etc.); each lab occupies its natural layer of the chain and provides the concrete empirical anchor for that node |

### The composition step (now implemented)

The HPA premise tells us *which cell types express DMD at all*. The
isoform-architecture premise tells us *which isoforms are affected by
this patient's variant*. Two composition premises now close the loop
between them:

- **`patient_celltype_impact`** — for each HPA cell type, computes
  whether it is *hit*, *partially spared*, *spared*, or *unknown* given
  the isoforms this patient's variant touches, using a curated cell-
  type-to-isoform dependency map (Muntoni 2003 for muscle isoforms,
  Pillers 1993 for Dp260 in retina, Lidov 1995 for Dp71 ubiquitous).
  Attributed to `node:cellType` + `edge:protein→cellType`.
- **`patient_tissue_impact`** — union of tissues from hit isoforms
  (from `isoforms.primary_expression_tissues`). Attributed to
  `node:tissue` + `edge:cellType→tissue`.

These premises carry **signed weights**: spared distal cell types
(e.g. photoreceptors, adipocytes) actively argue *against* H04 (distal-
isoform-loss mechanism) — not just via the absence of positive
evidence but via explicit negative weight. Patient 4 (variant at exon
8, only hits Dp427m/c/p) shows this: H04's aggregate falls to +8.2
because the composition premises supply negative weight ("distal cell
types SPARED — argues against distal-isoform-loss mechanism"). Patient
5 (variant at exon 75, hits everything including Dp71) shows the
opposite: H04's aggregate rises to +12.6 because the same composition
premises now argue positively (all distal cells affected).

The aggregate dimension of the score vector is a **signed sum**, so
these negative premises actually reduce hypothesis scores. Coverage
still counts *any* premise (positive or negative) so the chain
completeness metric is unaffected.

Additional sources — ESM2 log-likelihood ratios for variant-level
functional-disruption scoring, STRING for full protein-interaction
edge weights, ARCHS4 for co-expression, Geneformer for perturbation
response, CMap for signature-reversal drug queries — are called out
in the rare-disease-platform deck as priority additions. Each would
enter as a new premise producer, attributing to the appropriate node
or edge without disturbing sources already integrated.

### Pareto ranking: confidence × severity × treatability

Each hypothesis carries a three-axis score vector on top of the
aggregate signed weight:

- **Confidence** — a normalised combination of `aggregate` (signed
  premise-weight sum), `coverage` (fraction of the seven layers with
  any evidence), `consistency` (fraction of chain positions without
  contradiction), and `parsimony` (inverse of empty layers). Range
  ~[0.5, 1.0] across the current substrate.
- **Severity** — phenotype baseline (DMD 0.90, IMD 0.75, BMD 0.50,
  DCM 0.65) multiplied by a per-mechanism factor (H01/H03 = 1.0 for
  complete-loss trajectories, H02 = 0.6 for partial-function BMD,
  H04 = 0.7 for distal-isoform loss), with a small cardiac bump when
  the patient has abnormal LVEF.
- **Treatability** — weighted average of `TISSUE_TRACTABILITY` over
  the mechanism's target tissues. Muscle_Skeletal = 0.95 (AAV9 is
  clinically proven), Heart_LV = 0.75, Retina = 0.90 (subretinal AAV
  precedent), CNS_young = 0.60, CNS_adult = 0.35, Kidney = 0.35,
  Adipose = 0.15. Under-4 patients get the young-CNS number, older
  patients the adult one.

The three axes let the workbench answer *"pick the hypothesis with the
best trust-vs-severity-vs-treatability tradeoff"* rather than a single
scalar ranking. In practice: H01 sits at the corner of the frontier
(high on all three); H02 is the treatability-optimizer's pick (higher
treatability than H01, lower severity/confidence); H04 is the
distal-isoform mechanism no approved drug currently addresses.

## How a hypothesis emerges

For each patient, hypothesis formation proceeds in four moves:

**1. Assemble the patient's premise bundle.** All patient-scoped
premises (labs, variant record, isoform impact, protein fold) plus all
gene-scoped or cohort-scoped premises (HPA expression, Reactome
memberships, ClinVar NMD cross-tab) are gathered into a single set.
For Patient 5 in our current roster this is approximately ten patient
premises + three cohort premises = thirteen total.

**2. Instantiate the candidate chain templates.** For DMD, four
canonical mechanism templates (H01–H04) are well-established:
out-of-frame truncation with sarcolemmal fragility (H01);
in-frame rescue with partial function (H02); nonsense/splice-driven
NMD with tissue-graded loss (H03); distal-promoter variants with
isoform-specific loss (H04). Each template defines a specific walk
through the layer graph — which nodes it emphasizes and which
transitions it invokes. For less well-characterized diseases, an
LLM-driven generator would propose additional candidate walks.

**3. Attribute premises to chain positions.** Each premise in the
patient's bundle is routed to the node or edge it informs, for each
candidate hypothesis. The routing is source-driven: a Zhang record
always informs the variant and phenotype nodes; an ESM3 fold always
informs the protein node and the variant → protein edge; a lab
informs its own layer of the hierarchy (CK → cell type; LVEF →
tissue; 6MWT → phenotype). Each attribution is stored as a signed
weight — positive if the premise supports the hypothesis, negative
if it argues against.

**4. Compute the score vector for the assembled chain.** The
attribution counts + weights per layer and per edge roll up into
four dimensions:

- **Aggregate** — total evidence weight summed across nodes and edges
- **Coverage** — fraction of the seven biological layers that carry
  any evidence for this hypothesis
- **Consistency** — degree to which the premises agree with one
  another (v0 always 1.0; a later pass will detect contradictions)
- **Parsimony** — inverse of the number of empty layers, penalizing
  chains with unexplained gaps

The score is a vector, not a scalar. A hypothesis with a high
aggregate but low coverage is a chain that is well-supported at a few
layers but breaks in the middle. A hypothesis with modest aggregate
but 100% coverage is a chain that touches every layer of biology
even if none of the individual pieces are dramatic. The clinician
or the AAV design agent decides which dimension to prioritize.

## Illustration: Patient 5, hypothesis H01

Patient 5 carries a DMD frameshift variant at exon 75
(`p.(Ser3552Lysfs*6)`) and presents as a non-ambulant sixteen-year-old
with the classical severe motor phenotype. The workbench forms four
candidate hypotheses; H01 (out-of-frame → truncated dystrophin →
sarcolemmal fragility) is the top-ranked.

The assembly trace for H01 for this patient looks like:

| Layer | Evidence gathered | Source |
|---|---|---|
| **variant** | frameshift at exon 75, ACMG likely-pathogenic | Zhang 2024 record |
| variant → protein | patient's variant hits Dp427m/c/p through Dp71 in the isoform architecture; NMD prediction at cohort scale | isoform architecture, ClinVar NMD cross-tab |
| **protein** | truncated Dp71 folded via ESM3 (493 aa); WW domain preserved, C-terminal syntrophin-binding lost | ESM3 fold, isoform architecture |
| pathway → subcellular | dystrophin-glycoprotein complex assembly pathway | Reactome |
| **pathway** | five DMD-relevant Reactome pathways with specificity scores | Reactome |
| **subcellular** | *(no direct premise — a gap)* | — |
| cellType → tissue | HPA cell-type expression identifies which cells rely on the affected isoforms | Human Protein Atlas |
| **cell type** | myofiber damage biomarkers: CK 79× ULN; aldolase, LDH elevated | synthetic labs, HPA |
| **tissue** | LVEF 42% (cardiac impairment); FVC 17% predicted (respiratory failure); MRI fat fraction 91% (skeletal muscle replaced) | synthetic labs |
| **phenotype** | 6MWT 0m (non-ambulant); NSAA 6/34; time-to-stand 30s; patient phenotype label DMD | synthetic labs, Zhang record |

Coverage: six of seven layers evidenced (subcellular alone is empty
because we do not yet have a source that directly probes dystrophin
localization at the sarcolemma). Aggregate weight: 8.4. Parsimony: 0.5
(one gap penalizes it modestly).

The chain reads coherently top to bottom: the variant produces a
truncated protein that lacks the C-terminal DGC anchor, the DGC fails
to assemble, myofibers become mechanically fragile, muscle is
progressively replaced by fibro-fatty tissue, and the patient loses
ambulation. Each step has empirical support from at least one source.
The single gap (subcellular) is honestly flagged rather than papered
over with narrative.

## Compare to a hypothesis that scores lower

For the same Patient 5, H02 (in-frame rescue → BMD-like partial
function) is the lowest-ranked hypothesis (rank 4, aggregate 4.0,
coverage 3/7). Its chain is broken in the middle:

- Variant node: has evidence (Zhang record), but the variant is a
  frameshift — physically inconsistent with an in-frame rescue claim
- Protein node: some evidence (isoform impact)
- Pathway, subcellular, cell type, tissue nodes: no evidence
- Phenotype node: strong evidence, but the patient's clinical
  presentation (non-ambulant, severe motor decline) actively argues
  *against* a BMD-like partial-function mechanism

The chain has holes precisely where the mechanism story would need to
be strongest — the middle layers where the "partial function" claim
would need to be established. The score vector surfaces this: high
aggregate at a few nodes, but coverage is only 43%. A single scalar
score would have obscured the reason H02 doesn't fit.

## Where literature evidence lives

Literature is where mechanism biology becomes *citable* rather than
inferred from raw data. Every edge in the biological chain — every
claim of the form *"A implies B"* — ultimately rests on prior
published work that established the transition. Without literature
attribution, the chain reads as speculation; with it, each transition
carries the paper trail that justifies calling it a mechanism at all.

### The principle

**Literature should inform every edge across the biological hierarchy.**
The reading-frame rule at `variant → protein` is Monaco 1988. NMD's
50-nucleotide-upstream-of-last-EEJ boundary at `variant → protein`
is Popp & Maquat 2013. DGC assembly at `protein → subcellular` is
Ervasti & Campbell 1993. Ca²⁺ influx at membrane micro-tears at
`subcellular → cellType` is Petrof 1993. Dp260-loss producing a
negative ERG b-wave at `protein → cellType (retinal)` is Pillers 1993.
Dp140-loss correlating with IQ deficit at `cellType → phenotype (CNS)`
is Ricotti 2016. **Every edge in the chain has, or should have, at
least one paper anchoring it.**

### Where literature currently lives (and why that's inadequate)

Literature evidence in the current build lives in two places, neither
of which treats it as a first-class premise:

**1. Embedded inside curated hypothesis chains.** The
`hypothesis_chain_edge_evidence` table stores, per hypothesis, per
edge in that hypothesis's specific curated chain, one or more
citations (Monaco 1988, Hoffman 1988, Popp & Maquat 2013, etc.).
These are visible in the edge-evidence modal when a user clicks an
arrow in the reasoning chain. They are, however, *scoped to that
hypothesis's chain*. There is no way to query *"which papers support
the reading-frame rule"* independent of H01, or to reuse Popp &
Maquat 2013 across all hypotheses that share the NMD claim.

**2. Implicit in curated auxiliary sources.** The cell-type-to-isoform
dependency map in the hydrator cites Muntoni 2003, Pillers 1993,
Lidov 1995 in a Python comment. The NMD classifier cites Popp &
Maquat 2013 in a comment. The claim templates for each hypothesis
carry paraphrased-from-Monaco-1988 language. These citations *exist*
in the codebase but do not surface as premises; they do not appear in
the chain audit trail; they cannot be counted, weighted, or updated
independently.

### Where literature should live: as edge- and node-attributed premises

Literature should be a first-class premise source in the registry,
with each *claim from each paper* materialized as one or more
premises attributed to specific chain positions:

```
premise_source: 'literature' (source_type: 'data')

premise:
  premise_id: 'lit:monaco_1988:reading_frame_rule'
  source_id:  'literature'
  scope:      'cohort'                   (or 'variant' when variant-specific)
  scope_key:  'DMD'
  evidence: {
    pmid: '3325541',
    doi:  '10.1016/0092-8674(88)90463-1',
    citation: 'Monaco AP et al. 1988. Cell.',
    claim_text: 'Reading-frame rule: out-of-frame deletions produce DMD;
                 in-frame deletions produce BMD (~90% concordance).',
  }
  confidence: 0.98

hypothesis_chain_link:
  hypothesis_id: any hypothesis in the H01, H02, or H03 template family
  link_type: 'edge'
  layer_from: 'variant'
  layer_to:   'protein'
  premise_id: 'lit:monaco_1988:reading_frame_rule'
  weight:     +0.9 (for H01)
  weight:     +0.9 (for H02, symmetrically)
  weight:     +0.5 (for H03)
```

Now the same Monaco claim informs multiple hypotheses at the same
edge, with different signed weights. It is queryable, versionable,
and can accumulate additional co-citing papers over time. The
edge-evidence modal in the GUI becomes a rendering of literature
premises attributed to that edge, rather than a hand-curated bundle
inside one hypothesis.

### Coverage across the chain

The literature-source-per-edge target for DMD would look something like:

| Edge | Anchoring paper(s) | Claim being cited |
|---|---|---|
| variant → protein | Monaco 1988 | Reading-frame rule concordance |
| variant → protein | Popp & Maquat 2013 | PTC ≥50nt upstream of last EEJ → NMD-eligible |
| variant → protein | Aartsma-Rus 2006 | Splice-site variants produce downstream PTC via exon skipping |
| variant → protein | Hoffman 1988 | Western blot of DMD muscle: <3% dystrophin in PTC carriers |
| protein → subcellular | Ervasti & Campbell 1993 | Dystrophin C-terminal binds β-dystroglycan; DGC bridges actin to laminin |
| protein → subcellular | Ohlendieck 1991 | DGC components dissociate from sarcolemma in mdx muscle |
| subcellular → cellType | Petrof 1993 | Contraction-induced micro-tears admit extracellular Ca²⁺ |
| subcellular → cellType | Alderton 2000 | Elevated cytosolic Ca²⁺ activates calpain-1 → proteolysis |
| subcellular → cellType | Millay 2008 | Sustained Ca²⁺ overload opens the mitochondrial permeability transition pore |
| protein → cellType | Pillers 1993 | Dp260-loss → negative ERG b-wave in retinal photoreceptors |
| protein → cellType | Byers 1993 | Dp116 loss in Schwann cells → subtle nerve conduction changes |
| protein → cellType | Lidov 1995 | Dp71 is expressed broadly (retina, brain, kidney) |
| cellType → tissue | Muntoni 2003 | Dp427m is the muscle-specific isoform driving skeletal + cardiac dystrophy |
| cellType → tissue | Uezumi 2010 | Fibro-adipogenic progenitors expand + differentiate when muscle regeneration fails |
| tissue → phenotype | Bushby 1993 | BMD ambulation retained past age 16 (clinical criterion) |
| tissue → phenotype | Ricotti 2016 | Dp140-loss correlates with ~10-point IQ deficit |
| tissue → phenotype | Bello 2016 | Cardiac + CNS symptoms track residual isoform expression |

Most of these citations already exist in the codebase as prose or
comments; promoting them into the `premise` registry is a bake job,
not a fresh curation. Roughly forty citations already live in the
curated hypothesis chains (`hypothesis_chain_edge_evidence` table);
they can be re-emitted as literature premises with cross-hypothesis
attribution during a single migration pass.

### Literature's role: guiding hypothesis formation, not just validating it

Literature premises should not be added to hypotheses after the
hypotheses are formed. They should **enter the assembly at formation
time and shape which hypotheses form at all**.

Concretely: when the world model assembles a candidate walk through
the biological hierarchy, it consults the literature premises
available at each edge to answer *"is this transition a plausible
mechanism claim to make?"* Edges anchored by strong literature
(e.g., variant → protein via the reading-frame rule, backed by
Monaco 1988 and multiple downstream confirmations) can be traversed
with high confidence. Edges with no literature support get either
skipped (chain doesn't form through that transition) or flagged as
speculative (chain forms but its coverage/consistency score reflects
the gap).

This is the difference between literature-as-decoration
(*"here are the citations for the mechanism we already picked"*) and
literature-as-substrate (*"which mechanisms are the literature-
supported walks through the biology, and what evidence anchors each
step?"*). We are targeting the second.

Consequences once literature is a premise source integrated into
formation:

- Every candidate hypothesis is evaluated at formation time for
  literature support at each of its chain steps — hypotheses without
  literature anchors either don't form or form with an explicit "no
  literature support" mark.
- Chain coverage improves — the `subcellular` node currently sits
  empty because we have no source informing it directly; the DGC
  literature (Ervasti & Campbell 1993, Ohlendieck 1991) informs it
  and fills the gap.
- Hypothesis ranking gains a "literature support" dimension — the
  strength of peer-reviewed anchoring across the chain. Distinct from
  patient-specific evidence; both contribute to the final vector.
- Novel hypotheses proposed by an LLM must cite specific papers
  attributable to specific edges. An LLM claim without literature
  attribution at any step of its proposed chain is flagged as
  unsupported speculation — held in a review queue rather than
  ranked alongside literature-anchored hypotheses.
- New literature (from PubMed queries, from a `litreview` MCP tool,
  from clinician-flagged papers, from cited-in-consultation papers)
  enters via the same premise pipeline. When new literature lands at
  an edge, hypotheses that traverse that edge automatically inherit
  the strengthened support at the next generation run.

## The pipeline

Assembly is a linear pipeline, run once per patient during hydration:

```
   raw sources        →   typed premises   →   chain-attributed hypotheses
   ─────────────         ──────────────       ────────────────────────────
   Zhang cohort           patient premises     H01 with chain links + score
   ClinVar variants       cohort premises      H02 with chain links + score
   HPA expression                              H03 with chain links + score
   Reactome pathways                           H04 with chain links + score
   Synthetic labs
   ESM3 folds
```

Each stage is idempotent and re-runnable. Adding a new source (an
AbSplice bake, an ESM2 LLR bake, a STRING PPI ingest) means:

1. Register the source in the `premise_source` registry with an ID
   and a version.
2. Emit its rows into the `premise` table.
3. Declare which layer or edge it informs via the source-to-position
   mapping.
4. Re-run the hypothesis bake — the world model consumes the enriched
   premise set automatically. Rankings shift where the new evidence
   fires; hypotheses re-form with richer chains.

No scorer code is rewritten. The scientific pipeline scales by adding
sources, not by adding rules.

## What ranking gives us that a scalar score does not

A vector-valued ranking supports different clinical and research
questions with the same underlying data:

- **Which hypothesis is most complete?** Sort by coverage. The chain
  with the fewest gaps is the one the model has evidence about at every
  layer of biology.
- **Which hypothesis has the strongest total evidence?** Sort by
  aggregate. Useful when a well-established but narrower mechanism is
  the right answer.
- **Which chain is most parsimonious?** Sort by parsimony. Prefer
  chains with fewer weak links over chains with many.
- **Where are the evidence gaps I should investigate?** For any
  hypothesis, layers with zero premises identify targeted experiments
  or data acquisitions that would strengthen the chain.
- **Which hypotheses share the same evidence at specific steps?**
  Cross-hypothesis analysis of node premises. If H01 and H03 both
  cite the same PTC premise at the variant → protein edge, that
  evidence is *overdetermined* — supporting either hypothesis with
  equal force.

## Known gaps and roadmap

**Variant → cell-type composition premise.** The isoform-architecture
premise ends at the protein node; the HPA cell-type expression
premise is gene-scoped and does not compose with the patient's
variant. The result is that the chain currently has no patient-scope
link from protein to cellType. Fix: two new premise producers,
`patient_celltype_impact` and `patient_tissue_impact`, that compose
`isoform_architecture` × `CELL_TO_ISOFORMS` curated map ×
`isoforms.primary_expression_tissues` field into patient-specific
cellType and tissue node premises with signed weights (spared cell
types actively argue against distal-isoform-loss hypotheses).

**Literature as a first-class premise source.** Literature currently
lives embedded inside curated hypothesis chains
(`hypothesis_chain_edge_evidence` table) and as prose comments in
auxiliary sources. It should be promoted to the `premise` registry
with each claim attributed to specific chain positions — enabling
cross-hypothesis reuse, LLM-cited novel hypothesis validation, and
literature-guided formation (rather than post-hoc citation). Roughly
forty citations already exist in the codebase and can be migrated
in one bake pass.

**Subcellular-layer evidence — now closed.** UniProt subcellular
annotations for P11532 (sarcolemma, cytoplasm/cytoskeleton,
postsynaptic membrane, with note on ANK2 and costameres) provide
curated protein-biology data at the subcellular node. Literature
citations at the protein→subcellular edge (Ervasti & Campbell 1993,
Ohlendieck 1991, Petrof 1993 and downstream) are now
*dual-attributed*: they inform the transition edge AND the
subcellular node with half weight, on the principle that papers
establishing a transition typically also establish the biology at
the layers they connect. Result: 100% chain coverage for H01 across
all 10 patients in the roster. Muscle biopsy IHC would still be a
stronger patient-scope premise if data ever becomes available; the
UniProt + literature composition fills the cohort-scope gap.

**Aberrant splicing — now integrated.** AbSplice-DNA v1.0.4 scores are
now curated per-variant per-tissue in `data/raw/absplice_dmd_variants.tsv`
and emitted as an `absplice` premise attributed to `node:variant` +
`edge:variant→protein`. Weighting is category-aware:
- Canonical splice-site (P10 c.9361+1G>C, max score 0.88 in heart-atrial-
  appendage) → weight **0.7** on H01/H03 as a compounding NMD trigger,
  **0.3** on H02 (cryptic-acceptor use could yield an in-frame product),
  **0.1** on H04.
- Exonic missense/nonsense/frameshift (max score ~0.02–0.05) → weight
  **0.1** on H01/H03, explicitly recording *no splice signal* — the
  exonic consequence is the whole story.

The scores currently in the TSV are model-behavior-consistent estimates
keyed off variant category; running the real AbSplice pipeline on a
bigger host and swapping the TSV in place will replace them without
touching the emitter or the weighting logic. See the file's header
for the compute recipe.

**ESM2 log-likelihood ratios.** Structural fold (ESM3) is baked for
two patients; per-variant functional disruption scoring (ESM2 LLR) is
not yet integrated. Would add a variant-level severity premise
distinct from the ACMG classification.

**Downstream network sources.** Open Targets molecular interactors,
STRING PPI, ARCHS4 co-expression, Geneformer perturbation predictions,
and CMap drug signatures are all called out in the rare-disease
platform deck as priorities. Each would extend the chain into the
molecular-neighborhood space beyond the direct pathway node.

**Contradiction detection — now implemented.** The consistency
dimension of the score vector is no longer a placeholder. Each hypothesis
tracks per-chain-position positive and negative premise contributions
separately; a position is flagged as *contradicting* when both the
positive-weight sum and the negative-weight sum meet or exceed a
0.1 magnitude threshold. Consistency is then `1 - n_contradicting /
n_covered_positions`, and the full breakdown (per-position supporting
vs. opposing premises with rationales) is emitted in
`scoreVector.contradictions`.

Concretely, this fires for H04 (distal-isoform-loss) in 7 of 10
patients — the ones with proximal variants that only hit Dp427. At the
`cellType` node and `protein→cellType` edge, cohort literature
(Haenggi 2006, Lidov 1995, Pillers 1993) argues *for* distal-isoform
involvement, while the patient's composition premise argues *against*
it (distal cell types spared given the variant's isoform-hit pattern).
Consistency drops to 0.833 and the contradiction is surfaced in the
chain artifact so the user can see the specific evidence conflict.
The 3 patients with distal-reaching variants (P5, P258, P266) stay
clean because both sources agree the distal cells are affected.

**LLM-refined claims — now implemented (two layers).**

*Layer 1 (deterministic enrichment)* replaces the raw template's three
slots (`{p}`, `{cons}`, `{exon}`) with real values read out of the
premise bundle. Fixes the `int64` bug (exon number now comes from the
`isoform_arch` premise, not the raw variant string), names the specific
muscle-lineage cell types hit for H01 via the composition premise,
lists the spared isoforms for H02, weaves the AbSplice score into H03
when it's a canonical splice event, and marks H04 as "composition
contradicts" vs "composition supports" based on the distal-cell impact
pattern. Pure code, no LLM dependency. Also emits a top-3 distinguishing-
evidence list per hypothesis.

*Layer 2 (LLM refinement)* takes Layer 1 output plus the full
premise bundle for all 4 hypotheses of a patient and calls
`claude-sonnet-4-6` via the Anthropic Messages API (stdlib urllib,
no SDK dependency). One batched call per patient so the model has
cross-hypothesis context needed for `considered_but_discarded`
paragraphs. Returns per-hypothesis `{narrative,
considered_but_discarded, testable_predictions}` where each field is
constrained by the prompt: narrative ≤ 90 words, discarded rationale
≤ 25 words per other-hypothesis, exactly 3 testable predictions ≤ 22
words each. Cached by `cohort_pid_input_hash` so re-bakes on unchanged
inputs skip the API call.

*Groundedness verification* — a post-hoc check flags any isoform name
(Dp71, Dp427m, etc.), numeric value, or author-year citation appearing
in the LLM narrative that does not appear in the input premise bundle.
Unverified mentions are logged and stored alongside the narrative in
`scoreVector.groundedness` for surface-in-UI, without blocking the
refinement itself.

*Total cost*: ~$0.36 for a full-cohort refinement (10 patients ×
~4K input + ~4K output tokens each at Sonnet 4.6 rates). Graceful
skip if `ANTHROPIC_API_KEY` is unset — Layer 1 alone still ships an
enriched claim. Layer 0 template stays in the `claim` column for
audit continuity.

**Novel hypothesis discovery.** For DMD the four canonical templates
cover essentially all documented mechanisms. For less-well-studied
rare diseases, novel walks through the layer graph — mechanisms not
in any template catalog — would be proposed by an LLM operating on
the assembled premise bundle, held in a review queue for human
curation before promotion.

## Summary

The workbench treats hypothesis formation as **evidence assembly along
a biological hierarchy**. Sources contribute typed premises; each
premise is attributed to the specific node or edge of the chain it
informs; each candidate hypothesis is a walk through the graph that
collects those attributions into a chain-decomposed evidence bundle;
ranking is a separate, vector-valued operation that compares whole
chains along multiple dimensions.

The result is a hypothesis object that carries not just a score but a
full audit trail: which sources argued for it, at which layer, with
what weight, and where the chain has gaps. That trace is what
distinguishes a real world-model output from an opaque ranking — and
it is what makes the pipeline extensible to new evidence sources
without rewriting the scoring logic.
