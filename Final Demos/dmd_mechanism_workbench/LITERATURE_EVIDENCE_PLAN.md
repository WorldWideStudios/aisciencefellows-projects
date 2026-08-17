# Literature-backed edge evidence — bake plan

Status: **partially baked, blocked on paperclip service outage** (as of 2026-08-13).
Handoff doc for another agent to resume.

## Current bake state (2026-08-13)

The bake script `prototype/ingest/bake_dmd_edge_literature.py` exists and works.
128 of 562 planned queries completed before `paperclip status` began reporting
`Health: error`. All completed queries are cached under `cache/paperclip/` and
committed to `mechanism.sqlite::edge_literature_evidence` (591 paper hits, 345
distinct papers). The bake is idempotent — re-running skips already-completed
queries. **To resume**: check `paperclip status` returns `Health: ok`, then run
`~/venv/bin/python -u -m prototype.ingest.bake_dmd_edge_literature` (no --force).

| Edge type | Queries done | Papers kept | Avg/query | Status |
|---|---|---|---|---|
| celltype_tissue | 13 / 13 | 267 | 20.5 | **complete** |
| isoform_subcellular | 28 / 28 | 102 | 3.6 | **complete** |
| variant_isoform | 71 / 71 | 131 | 1.8 | **complete** — thin as expected |
| tissue_phenotype | 6 / 10 | 75 | 12.5 | 4 queries left |
| mech_phenotype | 10 / 40 | 16 | 1.6 | 30 queries left (mostly pilot data) |
| pathway_celltype | 0 / 400 | — | — | not started |

### Notable early findings

- **celltype_tissue is the richest edge**: Schwann cells → peripheral nerve (52 papers), cardiomyocytes → heart (48+), retinal ganglion cells (39), adipocytes (32). Kidney cell types (adrenal cortex/medulla, renal collecting duct) return **zero papers** — that's real signal, not a vocab bug; DMD renal literature is about podocytes + Dp71, not those specific cells.
- **Post-filter fix was needed**: initial pilot returned 0/100 kept because mechanism vocab (e.g. "sarcolemmal fragility") is too specific to appear in PMC abstracts verbatim. Added `DOMAIN_TOKENS = ["DMD", "dystrophin", "Duchenne", "dystrophic"]` as fallback from-vocab so mechanism-heavy edges pass. See `bake_dmd_edge_literature.py:_run_paperclip → filter loop`.
- **variant_isoform is thin because papers don't name isoforms in titles**. Dp427m is just "dystrophin" in most literature. Dp140/Dp71/Dp260 have specific literature and score better.

### Blocker

`paperclip status` returns `Health: error` (verified 2026-08-13 ~05:50 UTC).
This is a service-side issue, not something to fix in code. When paperclip
recovers, resuming the bake picks up where we left off. Estimated remaining
time when service returns: ~30–50 min at 5–8 sec/fresh-query.

### Scoring integration — NOT YET DONE

The bake writes evidence rows. Wiring `literature_edge_score` into
`hypothesis_frontier` (via SQL join into `edge_literature_evidence`) is the
next step after the bake completes. Existing PARETO_REFACTOR_PLAN.md
`hypothesis_strength` formula becomes:

```
hypothesis_strength = (agnostic_lit_edge_score + agnostic_node_evidence)
                    + patient_boost
```

where `agnostic_lit_edge_score = Σ_edge log(1 + n_papers_kept(edge))` summed
across the ~6 edges in this hypothesis's chain.

## Motivation

Current hypothesis scoring uses hand-curated `lit|<author>_<year>` premises
attached to 40 curated hypotheses (`hypothesis_chain_link` table). The
16,000 combinatorial frontier hypotheses have **no literature attribution**
— their scores are pure heuristic.

Fix: use `paperclip` (biomedical lit-search CLI) to query PMC for
publications that back each edge in the causal chain
(variant → isoform → subcellular → pathway → cellType → tissue → phenotype).
Publication count per edge becomes a defensible surrogate for evidence
strength — replaces the invented `mechanism_prior` and `severity_prior`
proposed in `PARETO_REFACTOR_PLAN.md`.

**Two-context distinction (user model):**
- **Node evidence** — evidence AT a layer (e.g. "cardiomyocytes express DGC members"). Already covered by existing `hypothesis_chain_link WHERE link_type='node'`.
- **Edge evidence** — evidence BETWEEN layers (e.g. "loss of DGC → cardiomyocyte injury"). Currently underpopulated for the 16k combinatorial rows. **This is what paperclip fills in.**

## Substrate

- `paperclip` CLI at `/home/ubuntu/.local/bin/paperclip` (already installed)
- Cache: `cache/paperclip/` — shared with ALMS1 project
- Template bake: `~/alms_inference_env/prototype/ingest/bake_mutant_paperclip.py`

## Query cap / rate policy
- 100 papers max per query (`-n 100`)
- No hard API budget (per user)
- Expect many nulls (that's meaningful — null = weak claim, real signal)
- Idempotent + cached — never re-query the same string twice

## Query templates (draft — iterate empirically)

| Edge | Query template | Est. # queries |
|---|---|---|
| **variant → isoform** | `"DMD exon {n} {isoform_name}"` (e.g. `"DMD exon 45 Dp427"`) | ~50 (representative exons × 10 isoforms, capped) |
| **isoform → subcellular** | `"dystrophin {isoform_name} {location}"` | ~40 (10 isoforms × 4 locations) |
| **pathway → cellType** | `"DMD {pathway_short_name} {cell_type}"` | ~200 (top 20 pathways × top 20 cell types, filtered) |
| **cellType → tissue** | `"DMD {cell_type} {tissue}"` | ~20 (already 1:1 in most cases) |
| **tissue → phenotype** | `"DMD {tissue} {phenotype_common_name}"` | ~30 (only plausible tissue-phenotype pairs) |
| **mech → phenotype** | `"DMD {mechanism_short} {phenotype_common_name}"` | ~40 (4 mech × 10 phenotypes) |

**Total first pass: ~350 queries** (subject to iteration).

## Post-filter (drops off-topic hits)

For each returned paper, keep only if title + summary mentions **both** endpoint terms of the edge. The substrate vocabulary comes from `celltype_expression` (cell types) + `pathways.sqlite` (pathway names) + fixed tissue/phenotype/isoform dicts.

## Output schema (new tables in `mechanism.sqlite`)

```sql
CREATE TABLE edge_literature_evidence (
  edge_type       TEXT NOT NULL,     -- 'variant_isoform' | 'isoform_subcellular' | 'pathway_celltype' | 'celltype_tissue' | 'tissue_phenotype' | 'mech_phenotype'
  from_layer_key  TEXT NOT NULL,     -- e.g. exon number, isoform name, pathway_id, cell_type
  to_layer_key    TEXT NOT NULL,
  query           TEXT NOT NULL,
  paper_id        TEXT NOT NULL,     -- PMC/DOI/arXiv id
  title           TEXT,
  authors         TEXT,
  paper_source    TEXT,              -- 'pmc' / 'biorxiv' / etc.
  date            TEXT,
  url             TEXT,
  summary         TEXT,
  matched_terms   TEXT,              -- JSON list of substrate vocab that matched
  PRIMARY KEY (edge_type, from_layer_key, to_layer_key, paper_id)
);

CREATE TABLE edge_literature_bake_meta (
  edge_type            TEXT NOT NULL,
  from_layer_key       TEXT NOT NULL,
  to_layer_key         TEXT NOT NULL,
  query                TEXT NOT NULL,
  n_papers_returned    INTEGER,
  n_papers_kept        INTEGER,      -- after post-filter
  baked_at             TEXT NOT NULL,
  PRIMARY KEY (edge_type, from_layer_key, to_layer_key)
);
```

## Scoring integration

After the bake, hypothesis strength gains a `literature_edge_score` component:

```
literature_edge_score(hyp) = Σ_edge log(1 + n_papers_kept(edge))
```

Summed across the ~6 edges in that hypothesis's chain. Log-scale so a
single well-studied edge doesn't dominate. Combined with existing
components:

```
hypothesis_strength = agnostic_lit_edge_score + agnostic_node_evidence + patient_boost
```

Hand-curated `lit|*` premises **kept alongside** paperclip results —
author-verified, zero noise, adds a high-confidence baseline. paperclip
extends coverage into edges the curated set doesn't reach.

## Execution checklist

- [x] **1.** Write `prototype/ingest/bake_dmd_edge_literature.py` (done — adapted from ALMS1's `bake_mutant_paperclip.py`)
- [x] **2.** Define query templates + endpoint vocabularies in module constants (done — see `ISOFORMS`, `SUBCELLULAR_LOCATIONS`, `TISSUE_TERMS`, `PHENOTYPE_TERMS`, `MECHANISM_TERMS` at top of bake file)
- [x] **3.** First pass: run with `--pilot` to validate templates + post-filter (done — surfaced the domain-token fix)
- [x] **4.** Post-filter fix landed: added `DOMAIN_TOKENS` fallback so mechanism-heavy edges pass
- [~] **5.** Full run: **partially complete** — 128/562 queries done, blocked on paperclip service outage. Resume with `~/venv/bin/python -u -m prototype.ingest.bake_dmd_edge_literature` (no --force) when `paperclip status` reports `Health: ok`
- [~] **6.** Verify per-edge-type hit distribution: **partial** — 3 edge types complete (see "Current bake state" above). pathway_celltype (400 queries) has not started.
- [ ] **7.** Update `bake_hypothesis_frontier.py` to compute `literature_edge_score` per row (SQL join into `edge_literature_evidence` grouped by hypothesis chain)
- [ ] **8.** Extend `hydrate_frontier_view.py` + `patient_chat.html` to expose lit-score in hover tooltip
- [ ] **9.** (Optional) Add a "publications backing" badge on each dot showing `n_distinct_papers`

## Known gaps / follow-ups

- paperclip results depend on PMC indexing recency. Some claims (Muntoni 2003) may return few results if the paper's abstract doesn't mention the exact term pair.
- Post-filter uses exact-string matching on title+summary. Consider embedding-similarity filter later (`--min-embedding-similarity 0.7`) for semantic match.
- H04 (distal isoforms Dp71/Dp140) has genuinely thin literature — that's real, not a bug. Score should reflect it.
- The `variant → isoform` edge attribution needs a rule for which exons are "representative" (all 79 DMD exons × 10 isoforms = 790 queries is too many). First pass: query only FDA-relevant exons (45, 51, 53) + isoform-boundary exons (30, 45, 56, 63) = ~30 queries.
- Query strings are English-only. Non-English PMC entries under-counted.
