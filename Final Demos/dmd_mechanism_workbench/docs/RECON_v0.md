# DMD / dystrophin — evidence recon (v0)

Companion doc for spinning up `~/dmd_inference_env/`, mirroring the ALMS1
substrate. Purpose: shortlist the data sources + primary literature we'd
actually pull from in Phases B–E, and flag known exceptions before we
bake anything.

Compiled 2026-07-25 from paperclip (PMC) + web search.

---

## 1. Variant catalogs (the "Marshall equivalent")

| Source | Access | Size | Notes | Priority |
|---|---|---|---|---|
| **LOVD-DMD** (Global Variome shared instance) | Public REST API, Atom+XML feed | **41,566 entries → 10,136 unique variants → 61,809 individuals** (confirmed 2026-07-25) | See §1a below — inspected. | **P0** |
| **TREAT-NMD DMD Global Database** | Registration + user agreement; releases *aggregate only* | 7,149 variants (2015 snapshot) | Bladen et al. 2015 (PMC4405042). Aggregate tables in the paper's supplementary material are machine-readable and public — use those, not the live registry. | **P1** |
| **UMD-DMD** | Public browse | ~large | Re-analyzed in Leckie et al. 2024 (PMC11593839) for exon-skip applicability. | **P2** |
| **eDystrophin** | Public browse | in-frame variants only | Nicolas et al. 2012 (PMC3748829). Adds structural-impact annotation for in-frame mutations; useful complement, not primary source. | **P2** |

### 1a. LOVD REST API — inspected 2026-07-25

**Deprecated route (do not use):** `https://databases.lovd.nl/shared/download/all/gene/DMD` responds `"Data for gene (DMD) is not public and you don't have permission to see non-public data."` — only accessible to gene curators.

**Live public route (single HTTP GET):**
```
GET https://databases.lovd.nl/shared/api/rest.php/variants/DMD
→ 200 OK, application/atom+xml, ~38 MB, no auth, no pagination
```

**Feed shape** — one `<entry>` per LOVD record, no `rel="next"`, closes cleanly:
```xml
<entry>
  <title>DMD:c.(?_-1289195)_(9085-18771_9085-1)dup</title>
  <link rel="alternate" href=".../search_VariantOnGenome%2FDBID=DMD_070330"/>
  <id>tag:databases.lovd.nl,2026-03-13:DMD/0001070741</id>
  <published>2026-03-13T19:47:53+01:00</published>
  <content type="text">
    symbol:DMD
    id:0001070741
    position_mRNA:NM_004006.2:c.-1289195_9085-18771
    position_genomic:chrX:120900001_138000000  ← often empty
    Variant/DNA:c.(?_-1289195)_(9085-18771_9085-1)dup
    Variant/DBID:DMD_070330
    Times_reported:1
  </content>
</entry>
```

**What we get:** `LOVD_id`, `DBID`, HGVS c-notation (relative to **NM_004006.2**, canonical Dp427m), cDNA range, `Times_reported`, curator, dates.

**What's MISSING from the API:**
- **No phenotype label** at the variant record level. `/shared/api/rest.php/individuals/DMD` returns HTTP 400 `"Requested data type not known"` — the REST API only exposes `/variants/`, not `/individuals/` or `/phenotypes/`. Phenotype metadata (DMD / BMD / IMD, age of onset, walking status) is **not accessible via API**.
- No exon annotations (only cDNA positions — we compute exon boundaries from NM_004006.2 exon table).
- No protein consequence (compute from HGVS).
- Ethnicity/regional origin not exposed.
- Genomic coords often empty.

**Phenotype workaround for Phase B:**
- **Bladen 2015** (PMC4405042) supplementary tables — 7,149 variants with DMD / BMD / IMD labels. Static snapshot, cite it.
- **ClinVar** via NCBI E-utilities — pathogenicity + clinical significance per HGVS. Should merge on HGVS c-notation.
- **UMD-DMD** — Leckie et al. 2024 (PMC11593839) re-analyzed for exon-skip applicability with phenotype metadata.

**HGVS parsing complexity:** entries range from simple SNV (`c.NNNNC>T`) to complex ambiguous-breakpoint structural (`c.(?_-1289195)_(9085-18771_9085-1)dup`). Recommend the biocommons `hgvs` library OR a regex-first parser that handles the common cases (~90% of the feed) and shelves unusual entries into an `unparseable/` bucket for manual review.

**Schema for `dmd_variants.tsv`** — different columns than Marshall because most variants are structural, not point:
```
variant_id, mut_type, exon_start, exon_end, cDNA, protein,
  in_frame_bool, predicted_class, reported_phenotype,
  cohort_count, source, source_ref
```
where `mut_type ∈ {del, dup, point, splice, dup_ins, complex}` and
`predicted_class ∈ {DMD, BMD, IMD}` (Monaco rule → next section).

---

## 2. Genotype→phenotype rule (Monaco reading-frame)

**The rule (Monaco 1988):** deletions/duplications that preserve the
reading frame yield truncated-but-functional dystrophin → Becker (BMD).
Frameshift deletions yield no functional dystrophin → Duchenne (DMD).

**Applicability:** works on ~90% of deletion patients as a first-pass
predictor. Not a stub — a first-class computed column.

**Known exceptions to bake as caveats:**
- **Δexon 5 (in-frame) → severe DMD phenotype.** Toh et al. 2016 (PMC4706350). The rule says "should be Becker-like"; reality is severe.
- **Apparent in-frame → out-of-frame at RNA level via aberrant splicing.** Yuan et al. 2025 (PMC12669050). Requires long-read RNA-seq to detect.
- **Δexons 52–55 mouse model → truncated dystrophin is insufficient for long-term muscle homeostasis** despite frame-preservation. Perillat et al. 2025 (PMC12519546).

**Implication for bake_dmd_frame_rule.py:**
Emit `predicted_class` from the rule, PLUS a `frame_rule_exception` boolean
tagged for a curated list of known-exception exon boundaries. Do not
overwrite the prediction — annotate.

---

## 3. Tissue atlases (parallel to Alström's four cxg files)

Three CellxGene collections should be enough for Phase C:

| Collection | Cell types of interest | h5ad size | Priority |
|---|---|---|---|
| **Tabula Sapiens** — `e5f58829-1a66-40b5-a624-9046778e74f5` | myofibers (I / IIa / IIx), satellite cells, FAPs, endothelial, macrophages (muscle slice) | large — slice muscle only | **P0** |
| **Human Skeletal Muscle Ageing Atlas** — `2d40e6a7-f2fd-49ba-9db9-6b97e4c6dad5` | denser myofiber subtypes, aged samples | medium | **P1** |
| **Heart Cell Atlas** (Litviňuková et al.) — `43b45a20-a969-49ac-a8e8-8c84b211bd01` | ventricular / atrial cardiomyocytes, fibroblasts, endothelial, macrophages | large | **P0** |

**Bake pattern:** reuse the h5py-direct sparse-slice approach from
`bake_cellxgene_portable.py`. Muscle is ~1 vCPU / 1.9 GB safe if we
slice by cell type on read, same as the Alström atlases. Heart may need
downsampling.

**Cell-type filter list** (analogue of the Alström tissue block/allowlist):
- **Allow (muscle):** skeletal_muscle_fiber_I, skeletal_muscle_fiber_IIa, skeletal_muscle_fiber_IIx, satellite_cell, FAP (fibro-adipogenic progenitor), tissue_resident_macrophage, endothelial_cell, muscle_stem_cell
- **Allow (cardiac):** ventricular_cardiomyocyte, atrial_cardiomyocyte, cardiac_fibroblast, endocardial_cell, cardiac_macrophage
- **Block:** blood-borne immune cells (unless studying inflammation cascade specifically), erythrocytes, generic stromal

---

## 4. Variant→cell-type causal evidence (the good stuff)

Where ALMS1 had ~7 papers, DMD has a curated stack of high-quality
Tier-2/3 evidence. Priority ranking below is by "how directly does this
paper support variant→cell-type inference in our pipeline."

### Tier 2A — human DMD snRNA-seq of patient biopsies (highest priority)

- **Suárez-Calvet et al. 2023 (PMC10482944)** — *"Decoding the transcriptome of Duchenne muscular dystrophy to the single nuclei level reveals **clinical-genetic correlations**."* snRNA of DMD biopsies with genotype metadata. **This is the DMD-equivalent of the paper I was wishing existed for ALMS1.** Land first.
- **Scripture-Adams et al. 2022 (PMC9485160)** — snRNA before/after exon-skipping ASO therapy. Cell-type-level rescue evidence: myofiber-type restoration, myeloid rebalancing, inflammatory-fibroblast reduction. **Directly links per-variant intervention → per-cell-type effect.**
- **Fernández-Simón et al. 2024 (PMC11264872)** — scRNA of human FAPs from DMD vs healthy. Functional stage stratification.
- **Fernández-Simón et al. 2026 (PMC12789545)** — snRNA-derived EGFR pathway upregulation in DMD; therapeutic-target framing.

### Tier 2B — mdx mouse scRNA-seq

- **Saleh et al. 2022 (PMC9646951)** — dystrophic mouse scRNA across disease severity spectrum. Cell-type compositional shifts with progression.
- **Esper et al. 2024 (PMC11669949)** — mdx muscle stem cell intrinsic dysfunction. Directly maps *loss of dystrophin* → *satellite cell polarity + numerical defect*.
- **Uapinyoying et al. 2023 (PMC10432818)** — FAP identity across tissues in dystrophy; Wnt-signaling dysfunction correlates with pathology.

### Tier 2C — patient iPSC-derived cell models

- **Dhoke et al. 2024 (PMC11171783)** — CRISPR correction of downstream-exon-44 variants in patient-specific iPSCs. **Per-variant, per-cell-type causal readout.** The DMD equivalent of Dargar 2026 for ALMS1, but with more variants.
- **Gilbert et al. 2021 (PMC8599983)** — DAPC assembly failure in DMD iPSC-CMs (2D + 3D). Molecular mechanism at the cardiomyocyte level.
- **Andrysiak et al. 2024 (PMC11259739)** — utrophin upregulation rescues DMD iPSC-CM phenotype. Establishes utrophin as a druggable target with cell-type-level readout.
- **Eisen & Binah 2023 (PMC10218670)** — review of DMD iPSC-CM modeling. Use for citations, not primary data.

### Tier 4 — cohort-level population statistics

- **Bladen et al. 2015 (PMC4405042)** — TREAT-NMD 7,149-variant analysis. Deletion frequencies per exon.
- **Leckie, Zia, Yokota 2024 (PMC11593839)** — updated UMD-DMD exon-skipping applicability analysis (~90% of deletions/small lesions in principle addressable by single or double skips).

---

## 5. Exon-skipping / ASO druggability priors (real, not stub)

Approved ASOs → per-exon druggability column becomes tractable:

| ASO | Target skip | Applicable to | FDA status |
|---|---|---|---|
| **Eteplirsen** (Exondys 51) | exon 51 | ~13% of DMD deletions | Approved 2016 |
| **Golodirsen** (Vyondys 53) | exon 53 | ~8% | Approved 2019 |
| **Viltolarsen** (Viltepso) | exon 53 | ~8% | Approved 2020 |
| **Casimersen** (Amondys 45) | exon 45 | ~8% — PMC11048227 | Approved 2021 |
| **Brogidirsen** (Phase 1/2) | exon 44 | ~6% — PMC11866436 (2025) | Investigational |
| **Elevidys** (delandistrogene) | whole-gene micro-dystrophin | broad | Approved 2023 (accelerated) |
| **Ataluren** | nonsense readthrough | ~10% (stop codons) | Conditional EU |

**Population coverage (from web search):**
- Deletion hotspot at exons **43–55 covers ~70% of deletions**.
- **Single-exon deletions ~19%**, most at exons 51, 44, 45.
- **Δ45–55 multi-exon skip theoretically addresses ~63–65% of deletion patients** (van Vliet 2008 PMC2611974; Echigoya 2018 PMC6313462; Adkin 2012 PMC3488593). Not yet clinical.

**Column for variant table:**
```
skippable_exons          -- list of exons whose skip would restore frame
approved_aso_available   -- {eteplirsen | golodirsen | viltolarsen |
                             casimersen | ataluren | elevidys | null}
druggability_score       -- derived from above; real value, not stub
```

---

## 6. Delta from ALMS1 substrate

**Same / reusable as-is:**
- Pathways bake (`bake_pathways.py`) — Reactome + GO-BP + KEGG works identically for DMD.
- `_common.py` sparse group_stats + SQLite schema.
- ESM3 server contract.
- MCP server structure (5 servers).
- Workbench UI + Pareto scoring skeleton.

**New / different:**
- Variant table schema (structural variants, not just SNVs).
- Frame-rule bake (`bake_dmd_frame_rule.py`) — new; no ALMS1 analog.
- Skip-amenability bake — new; needs published amenability tables.
- Hypothesis bake can *cite* observed evidence (Suárez-Calvet, Scripture-Adams, Dhoke, Gilbert) — not just mechanistic inference. Bake a `causal_evidence` table analogous to the one I proposed for ALMS1 but populated from day one.

**Same-shape but different-source:**
- Tissue atlases → cellxgene muscle + heart instead of eye/kidney/liver/pancreas.
- GTEx equivalent → GTEx muscle already sits inside Tabula Sapiens; no separate bake.

---

## 7. Concrete Phase B plan (what "spin up dmd_inference_env" means)

Order of ops:

1. `mkdir ~/dmd_inference_env/` with the same layout as `~/alms_inference_env/`.
2. Adapt CLAUDE.md → replace ALMS1-specific paragraphs with DMD equivalents; keep the resource-caution paragraph verbatim.
3. Copy `prototype/ingest/_common.py`, `bake_pathways.py`, `bake_cellxgene_portable.py` unchanged.
4. Write `prototype/ingest/dmd_download_lovd.py` → pulls the LOVD-DMD bulk export, lands `data/variants/dmd_variants_raw.tsv`.
5. Write `prototype/ingest/bake_dmd_variants.py` → normalizes raw LOVD to our schema, computes Monaco rule + frame-rule-exception flag, joins skip-amenability, emits `data/variants/dmd_variants.sqlite`.
6. (Deferred to Phase C) — bake Tabula Sapiens muscle + Heart Cell Atlas via h5py-direct.

Estimated Phase B compute: **negligible.** LOVD download is a few MB; variant normalization is CPU-trivial.

---

## Open questions to close before Phase B

1. **Repo template extraction:** postpone until after DMD is standing (rule of two).
2. **LOVD download format:** need to verify their bulk export is still in LOVD import format and machine-parseable. May need to inspect the actual file before writing the parser.
3. **Which UniProt for dystrophin:** ~~canonical Dp427m~~ **all seven major isoforms in scope for v0** (user decision 2026-07-25). See §8 below.

---

## 8. Dystrophin isoform table (v0 scope)

Seven major isoforms from seven distinct promoters. LOVD anchors variants
to NM_004006.2 (Dp427m); per-isoform effect is computed locally from the
exon-usage map, not from re-downloaded feeds.

| Isoform | RefSeq | UniProt | Promoter tissue | Primary expression | Phenotype relevance |
|---|---|---|---|---|---|
| **Dp427m** | NM_004006 | P11532-1 | Muscle | Skeletal + cardiac muscle | Muscle weakness, cardiomyopathy |
| Dp427c | NM_000109 | P11532-2 | Cortical | Cortical neurons, hippocampus | Cognitive phenotype |
| Dp427p | NM_004009 | P11532-3 | Purkinje | Cerebellar Purkinje cells | Cerebellar contribution |
| Dp260 | NM_004010 / NM_004011 | P11532-5 | Retinal | Photoreceptors | ERG abnormalities |
| Dp140 | NM_004012 / NM_004013 | P11532-6 | Brain/kidney | Glia, kidney | Cognitive severity |
| Dp116 | NM_004014 | P11532-7 | Schwann | Peripheral nerve | Peripheral nerve involvement |
| Dp71 | NM_004015 (Dp71a) / NM_004016 (Dp71b) | P11532-8 | Ubiquitous | Retina, brain, kidney, liver, blood | Multi-tissue short isoform |

**Design implication:** we do NOT re-pull LOVD per isoform. LOVD stores
each variant once, anchored to NM_004006.2. We instead build a
`dmd_exon_usage.tsv` table (exon × isoform boolean) and compute
`affects_isoform_X` per variant by intersecting the variant's cDNA range
with the exons each isoform uses.

---

## 9. Phase B — serialized step list (resource-safe)

Post-reboot rule: **one step at a time, one bash command at a time, no
background parallelism.** Ask for go between steps.

**B.0** `mkdir ~/dmd_inference_env/` with the layout (no compute).
**B.1** Move `/home/ubuntu/dmd_recon_v0.md` → `~/dmd_inference_env/docs/RECON_v0.md`.
**B.2** Copy `CLAUDE.md` from alms env, adapt paragraphs (~5 min manual edit — no compute).
**B.3** Copy disease-agnostic ingest helpers (`_common.py`, `bake_pathways.py`, `bake_cellxgene_portable.py`) — cp only.
**B.4** Re-download LOVD atom feed (38 MB, single curl, into `data/raw/dmd_lovd_atom.xml`).
**B.5** Write + author-review `prototype/ingest/dmd_isoforms.py` — the static isoform + exon-usage table.
**B.6** Write + author-review `prototype/ingest/parse_lovd_atom.py` — regex-first parser, streams the XML (not full parse), emits `data/variants/dmd_variants_raw.tsv`.
**B.7** Fetch Bladen 2015 supp table (small download, one file).
**B.8** Write `bake_dmd_variants.py` — merges raw LOVD + Bladen phenotype + isoform effect + Monaco rule → `data/variants/dmd_variants.sqlite`.
**B.9** Smoke query on the sqlite: row counts per (isoform, in_frame, phenotype_label).
