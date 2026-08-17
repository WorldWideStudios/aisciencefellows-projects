# dmd_inference_env — Claude orientation

Inference-oriented architecture for **Duchenne muscular dystrophy (DMD /
dystrophin)**, mirroring the design of the sibling repo
`~/alms_inference_env/` (which itself mirrors JARVIS_for_bio). Variant →
transcript (single-cell expression) → protein (all seven isoforms) →
per-variant markdown report.

Full recon that seeded this env: `docs/RECON_v0.md`. Read it first.

## Box constraints (read before touching data)

This dev host is **1 vCPU / 1.9 GB RAM**. Two prior reboots (both on
`~/alms_inference_env/` work) forced hard restarts. The relevant
compute split for DMD:

- **On this box**: bake the CellxGene muscle + heart atlases via
  h5py-direct (no scanpy import), per-cell-type sparse slices only.
  Parse the LOVD Atom feed (streamed, not full-DOM). All ESM3 calls
  (Forge is remote), MCP servers, and report composition fit comfortably.
- **On a separate ≥ 8 GB host** *(if needed later)*: heavy multi-tissue
  scans, whole-transcriptome integrations. TBD when we hit a limit.

**Never** import scanpy / anndata / numba and slice a multi-tissue h5ad
on this box in the same Python process. **Never** kick off more than 2
background bash jobs at a time, and never combine backgrounded jobs
with a multi-MB curl/WebFetch burst in the same message — bursts of
lightweight parallelism have frozen this box. If a step looks risky,
announce and wait for explicit "go" before running it.

## Scope: all dystrophin isoforms

Unlike the ALMS1 env (single canonical isoform), DMD v0 tracks all
**seven major isoforms** from a shared LOVD anchor:

| Isoform | RefSeq | Promoter tissue | Phenotype relevance |
|---|---|---|---|
| Dp427m | NM_004006 | Muscle | Muscle weakness, cardiomyopathy (**LOVD anchor**) |
| Dp427c | NM_000109 | Cortical | Cognitive |
| Dp427p | NM_004009 | Purkinje | Cerebellar |
| Dp260 | NM_004010 / NM_004011 | Retinal | ERG abnormalities |
| Dp140 | NM_004012 / NM_004013 | Brain/kidney | Cognitive severity |
| Dp116 | NM_004014 | Schwann | Peripheral nerve |
| Dp71 | NM_004015 / NM_004016 | Ubiquitous | Multi-tissue short isoform |

LOVD stores each variant once, anchored to NM_004006.2 (Dp427m). We
compute `affects_isoform_X` per variant locally, via an
`exon × isoform` usage table — **do not re-download LOVD per isoform**.

## Architecture

Three MCP servers + one workflow, all wired through pre-computed indices.
At hypothesis time the agent only reads; reasoning happens once, at the
end. Same contract as the ALMS1 env — a v1 refactor may generalize a
shared library.

| Server | Status | Tools (planned) |
|---|---|---|
| `esm3` | planned (port from JARVIS_for_bio) | `variant_consequence`, `uniprot_sequence`, `fold_and_annotate`, `render_variant_png`, `score_target` |
| `expression` | planned (SQLite-backed) | `expression_for_gene`, `top_cell_types_for_gene`, `sources_and_tissues`, `expression_per_isoform` |
| `pathways` | planned (SQLite-backed, reuse alms bake) | `pathways_for_gene`, `genes_in_pathway` |
| `variants` | planned (DMD-specific) | `variants_for_exon`, `monaco_rule`, `skip_amenability`, `isoform_effects` |

## Data substrate

| File | Built by | Contents |
|---|---|---|
| `data/raw/dmd_lovd_atom.xml` | `prototype/ingest/download_lovd_atom.py` | 38 MB Atom feed, 41,566 entries, 10,136 unique DBIDs |
| `data/variants/dmd_variants_raw.tsv` | `prototype/ingest/parse_lovd_atom.py` | one row per LOVD entry: LOVD_id, DBID, HGVS, cDNA range, Times_reported |
| `data/variants/dmd_isoforms.tsv` | `prototype/ingest/dmd_isoforms.py` | 7 rows: isoform, RefSeq, promoter tissue, exons used |
| `data/variants/dmd_exon_usage.tsv` | `prototype/ingest/dmd_isoforms.py` | exon × isoform boolean matrix |
| `data/variants/dmd_bladen2015.tsv` | `prototype/ingest/fetch_bladen_supp.py` | ~7,149 rows with DMD/BMD/IMD phenotype labels |
| `data/variants/dmd_variants.sqlite` | `prototype/ingest/bake_dmd_variants.py` | joined table: LOVD + Bladen + isoform effect + Monaco rule + skip amenability |
| `data/expression.sqlite` | `prototype/ingest/bake_cellxgene_portable.py` (reused) | per-cell-type expression from muscle + heart atlases |
| `data/pathways.sqlite` | `prototype/ingest/bake_pathways.py` (reused unchanged) | Reactome + GO-BP + KEGG |
| `cache/esm3/<uniprot>/` | `esm3.fold_and_annotate` | `structure.pdb`, `function.json`, `render_*.png` |

`source` values planned in `gene_celltype_expression`: `cxg_tabula_sapiens_muscle`, `cxg_muscle_ageing`, `cxg_heart_atlas`.

## Conventions (adapted from JARVIS via alms_inference_env)

**1. Workflow before action.** When given a variant or a question, the
first move is to look up the registered workflow, present its step list,
and wait for "go" before any MCP call.

**2. Provenance over invention.** Every report claim cites the MCP tool
that produced it. If an index returns no rows, say so honestly. Cell
type IDs carry Cell Ontology terms where available; cross-source claims
about "the same" cell type are approximations — flag that.

**3. Reasoning is the final step.** The retrieval steps are pure
ID-passing. The agent reasons only at the composition step, over the
evidence pack already assembled. Don't reason ahead of the data.

**4. Honest stubs.** Unlike ALMS1 v0 (where causal evidence was
scarce), DMD has real per-variant and per-cell-type observed evidence
from Suárez-Calvet 2023, Scripture-Adams 2022, Dhoke 2024, Gilbert 2021,
et al. — cite those, don't manufacture links from cross-products.

**5. Monaco rule with exceptions.** The reading-frame rule holds for
~90% of deletions but has published exceptions (Δexon 5 in-frame →
severe DMD; apparent in-frame → out-of-frame at RNA level via aberrant
splicing). Emit the rule prediction PLUS a `frame_rule_exception`
annotation — never overwrite one with the other.

## Iteration 1 status

Scaffolding complete (2026-07-25). Recon doc landed (`docs/RECON_v0.md`).
Phase B in progress: LOVD atom download + parser + Bladen merge + isoform
computation + Monaco rule → `dmd_variants.sqlite`. See RECON_v0.md §9 for
the serialized step list.

## Active refactors (2026-08-13)

Two in-flight scoring changes that touch the Pareto — Hypotheses view.
Both have plan docs in the repo root:

- **`PARETO_REFACTOR_PLAN.md`** — **shipped**. Two-objective refactor:
  X = hypothesis_strength (`weighted_fit × xlab_bonus + confidence`),
  Y = aav_viability (`tissue_delivery × payload_fit × dgc_rescue ×
  precedent × tissue_target_boost × rescue_window`). Both axes maximised;
  ideal hypothesis sits top-right. Per-patient Pareto sweep in JS
  (`frontierComputePareto` in `workbench/patient_chat.html`) sorts by X
  DESC, sweeps tracking best-Y-seen, keeps strictly improving points.

- **`LITERATURE_EVIDENCE_PLAN.md`** — **partial, blocked**. Replaces
  hand-set mechanism_prior/severity_prior with real publication-count
  evidence per chain edge, via paperclip → PMC. 128/562 queries baked;
  paperclip service reports `Health: error` as of this write. Resume
  with `~/venv/bin/python -u -m prototype.ingest.bake_dmd_edge_literature`
  when paperclip recovers — bake is idempotent, cached under
  `cache/paperclip/`. Scoring integration (join into
  `hypothesis_frontier`) not yet wired.

## Literature-search tool

`paperclip` CLI (at `/home/ubuntu/.local/bin/paperclip`) is the sanctioned
biomedical-lit tool. Same cache layout as `~/alms_inference_env/`
(`cache/paperclip/<sha1(query|source|n)>.json`). Check `paperclip status`
before large query bursts — the service has periodic outages.

## Where things live

```
docs/
  RECON_v0.md                      # evidence recon (READ FIRST)
CLAUDE.md                          # this file
.mcp.json                          # (planned) Claude Code MCP wiring
data/
  raw/                             # gitignored — LOVD atom, atlas h5ads
  variants/
    dmd_variants_raw.tsv           # LOVD normalized
    dmd_isoforms.tsv               # in git
    dmd_exon_usage.tsv             # in git
    dmd_bladen2015.tsv             # in git (phenotype labels)
    dmd_variants.sqlite            # gitignored — baked
  expression.sqlite                # gitignored — baked
  pathways.sqlite                  # gitignored — baked
cache/esm3/                        # gitignored — fold + render cache
prototype/
  ingest/
    download_lovd_atom.py          # (B.4) pull the 38 MB Atom feed
    parse_lovd_atom.py             # (B.6) stream-parse XML → raw TSV
    dmd_isoforms.py                # (B.5) static isoform + exon-usage
    fetch_bladen_supp.py           # (B.7) Bladen 2015 supp table
    bake_dmd_variants.py           # (B.8) join + Monaco rule + isoform effect
  mcp_servers/                     # (planned) 4 servers
  workflows/                       # (planned)
  scripts/
    probe_*.py                     # (planned) sanity checks
output/                            # gitignored — per-variant reports
```

## Sibling repo

`~/alms_inference_env/` is the parallel disease environment for Alström
syndrome. Same architecture, different indices. **Rule of two**: build
DMD by hand first, extract a shared template only after both are stable.
Don't premature-unify the schemas.

## When you're not sure

If a step is heavy, ask first. If a memory file says don't do something,
don't do it. If the user wants a stub turned into a real index, that
usually means writing one more bake script — not changing the MCP server
contract.
