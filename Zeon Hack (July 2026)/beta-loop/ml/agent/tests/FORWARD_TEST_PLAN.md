# Forward research agent — test plan (v1)

**Agent:** `forward_agent` (`ml/agent/`)  
**Version label:** `forward-research-agent-v1`  
**Frozen snapshot:** [`ml/workflows/compound_selection/snapshots/forward/v1/`](../../../ml/workflows/compound_selection/snapshots/forward/v1/manifest.json)  
**Owner:** Philip (pvjthomas)

This document is the v1 test plan for the forward pass (literature → library matching). Implementation: grouping + caps in `tools/forward.py`; pytest suite in `ml/agent/tests/` (run with `.venv/bin/python`, not system Python).

---

## Scope

Forward v1 answers: *Which published TEM-1 inhibitors do we already have on the shelf, and what literature supports them?*

| In scope (v1) | Out of scope (v1) |
|---------------|-------------------|
| Seed reference inhibitors | Reverse pass (RDKit scaffold tags) |
| Name / synonym / Tanimoto library matching | GNINA docking |
| Related-form linking for in-library alternates | Full-library Paperclip sweep |
| Per-compound ref JSON (structured, git) | Merge / plate design |
| v1 manifest snapshot | Round 1 / Round 2 screening |

---

## Alternate forms policy

Compounds often appear under multiple names or salt forms. Forward v1 treats these differently depending on **where** the alternate form lives.

### Case A — Alternate forms are separate library compounds

**Do not download or characterize literature twice.** One literature pass per *chemical group*; library alternates cross-reference each other.

Example (clavulanate group):

| compound_id | name | Role |
|-------------|------|------|
| **T19860** | Clavulanic Acid | **Canonical** — primary ref file, literature download target |
| T14979 | Clavulanate lithium | Alternate form — `related_forms` pointer to T19860 |

Example (sulbactam group):

| compound_id | name | Role |
|-------------|------|------|
| **T1631** | Sulbactam | Canonical (free base) |
| T6685 | Sulbactam sodium | Alternate form — pointer to T1631 |

**Rules:**

1. Pick one **canonical compound_id** per group (prefer free acid / base name over salt when both are in-library).
2. Store curated literature on the canonical ref: `data/compound_literature/refs/{canonical_id}.json`.
3. Alternate library IDs get a **thin ref file** or inline block:

```json
{
  "compound_id": "T14979",
  "match": "yes",
  "support": "strong",
  "form_type": "lithium_salt",
  "canonical_compound_id": "T19860",
  "related_forms": ["T19860", "T14979"],
  "note": "Li+ salt of clavulanic acid; assay priors same as T19860.",
  "entries": []
}
```

4. `state.json` → `forward.compound_groups[]` records the group once; flat `matches[]` may still list each reference name but must include `group_id` and `canonical_compound_id`.
5. v1 manifest `ref_compound_ids` lists **unique** IDs only (no duplicates for the same group).
6. **Paperclip searches** run once per group (query uses canonical name + known synonyms), not once per library well.

### Case B — Alternate form exists in literature only (not in library)

**Download and characterize literature** for that literature-only structure. It cannot cross-ref to a library ID.

Example: literature reports "avibactam" but library has no avibactam vial.

**Rules:**

1. Record in `forward.library_matches.literature_only[]` or a dedicated `literature_only_forms[]` entry.
2. Run a **group-specific Paperclip query** (canonical literature name).
3. Write a literature-only stub under `data/compound_literature/refs/_literature_only/{normalized_name}.json` **or** hold in `state.json` until bridge_agent assigns a Tanimoto analog.
4. Raw Paperclip output → `pvjthomas/local/literature/_literature_only/{name}/` (gitignored).
5. Counts toward **per-compound literature budget** (see caps below).

### Detecting related forms (implementation order)

1. **Manual overrides** — `literature_summary.json` → `compound_assay_priors` (e.g. T14979 note → T19860).
2. **Salt-stripped name cluster** — `normalize_name()` strips `sodium`, `lithium`, `hydrate`, etc.; cluster library IDs with identical stripped cores.
3. **RDKit Tanimoto ≥ 0.85** between library SMILES (same core, different counterion).
4. **Canonical tie-break** — free acid/base > named salt; higher `support` curation > auto-generated stub.

---

## Literature download caps (v1)

Yes — set explicit caps so git stays small and Paperclip cost is predictable.

### Tier 1: Paperclip search (API)

| Parameter | v1 cap | Notes |
|-----------|--------|-------|
| Batch forward queries | **2** | `FORWARD_QUERIES` in `forward.py` (F1) |
| Per-query result limit | **15** | Current default; hard max **20** (`literature.py`) |
| Per-group extra query (literature-only form) | **1** | Only when form not in library |
| **Max Paperclip searches per forward v1 run** | **6** | 2 batch + up to 4 literature-only groups |

Record in `state.forward.literature_searches`: `elapsed_ms`, `result_id`, `query`, `limit` per search (for cost/latency tests).

### Tier 2: Structured ref JSON (git-tracked)

Per **canonical** compound_id (e.g. `T19860.json`):

| Field | v1 cap | Rationale |
|-------|--------|-----------|
| `entries[]` (curated citations) | **5** | Primary TEM-1 evidence + 1–2 supporting class-A papers |
| `entries` with full extraction (Ki/IC50) | **3** | Enough for assay priors; rest title-only |
| `assay_recommendations` blocks | **1** | Project assay (`tem1_nitrocefin`) |
| File size (git) | **≤ 50 KB** | Aligns with [`data/STORAGE.md`](../../../data/STORAGE.md) summary rule |

Alternate library forms (Case A): **0 entries** — pointer only.

### Tier 3: Raw / full-text downloads (local, gitignored)

Per canonical compound_id under `pvjthomas/local/literature/{compound_id}/`:

| Asset | v1 cap | Notes |
|-------|--------|-------|
| Raw search dumps (`.txt`) | **2** | One per query that returned hits |
| Full-text downloads (BioC-XML, PDF) | **2** | Primary paper + one supporting |
| Total local folder | **≤ 5 MB** | Regeneratable; delete oldest if exceeded |

Literature-only forms (Case B): same caps, under `_literature_only/{name}/`.

### When cap is hit

1. Keep highest-priority entries: TEM-1 direct > class A other > general β-lactamase.
2. Set `support: "weak"` and `cap_truncated: true` on the ref file.
3. Log skipped PMIDs in `state.forward.literature_searches.truncated[]`.

---

## Manual benchmark: clavulanic acid (T19860)

Use a **minimal library subset** for fast, deterministic tests — not the full 105-compound CSV.

### Fixture library (6 compounds)

| compound_id | name | Why included |
|-------------|------|--------------|
| T19860 | Clavulanic Acid | **Gold standard** — curated ref, Ki = 0.85 µM |
| T14979 | Clavulanate lithium | Alternate form (Case A) |
| T1262 | Tazobactam | Known inhibitor |
| T14081 | Enmetazobactam | Substring false-positive guard vs tazobactam |
| T6685 | Sulbactam sodium | Salt form grouping |
| T19709 | Nitrocefin | Excluded (`exclude: true`) |

### Gold assertions (T19860)

| Check | Expected |
|-------|----------|
| Canonical ID | T19860 |
| Related forms | T14979 linked; group_id `clavulanate` |
| Curated ref preserved | PMID **40484381** still in `entries` after match |
| Ki prior | 0.85 µM (Radojković et al. 2025) |
| Literature download | ≥ 1 full-text in `downloads[]` (PMC12274840) |
| Assay @ 50 µM | `expected_at_50uM`: ≥50% inhibition |

Fixture paths (to create when implementing tests):

```
ml/agent/tests/fixtures/
  compounds_clavulanate_subset.csv
  literature_summary_clavulanate.json
  refs/T19860.json          # copy of curated benchmark
```

---

## v1 artifact contract

After `finalize_forward_run(version=1)`, these paths must exist:

```
ml/workflows/compound_selection/snapshots/forward/v1/
  manifest.json
  reference_inhibitors.csv
  state_forward.json
  literature_summary_patch.json
  refs/{compound_id}.json   # unique IDs only
```

### manifest.json required fields

- `agent`: `"forward_agent"`
- `version`: `1`
- `label`: `"forward-research-agent-v1"`
- `status`: `"complete"`
- `files`: all listed paths exist
- `match_count`, `literature_only_count`
- `ref_compound_ids`: **deduplicated** sorted list

### state.json forward section (active + snapshot)

- `forward.library_matches`
- `forward.agent_version`: `"v1"`
- `forward.run_label`: `"forward-research-agent-v1"`
- `forward.manifest`: `"ml/workflows/compound_selection/snapshots/forward/v1/manifest.json"`
- `forward.finalized_at`
- `forward.compound_groups[]` (once implemented)

---

## Test tiers

### Tier 1 — Unit tests (CI, no network, tmp_path only)

Never write to repo `data/`; monkeypatch `agent.paths` to tmp fixtures.

| Module | Tests |
|--------|-------|
| Name matching | enmetazobactam → T14081 not T1262; clavulanic → T19860 preferred |
| Form grouping | clavulanate group {T19860, T14979}; sulbactam group {T1631, T6685} |
| Curated ref guard | match does not overwrite T19860 Paperclip entries |
| Cap logic | truncates at 5 entries / flags `cap_truncated` |
| Deduplication | manifest `ref_compound_ids` unique |

### Tier 2 — Offline pipeline integration (CI, tmp_path)

Run: `seed_reference_inhibitors` → `match_literature_to_library` → `write_literature_summary_from_forward` → `finalize_forward_run(version=1)`.

Assert full v1 artifact tree + state fields + clavulanic gold assertions.

### Tier 2.5 — Screen subset integration (CI, tmp_path)

**Library:** 23 compound IDs from [`data/screens/1/v3/plate_map.json`](../../../data/screens/1/v3/plate_map.json) → `fixtures/compounds_screen_v3_subset.csv`.

**Fixture:** `screen_workspace` — v3 plate compounds + project `literature_summary.json` + curated T19860 ref.

| Check | Expected |
|-------|----------|
| Tier-1 inhibitor wells (B1–B4) | T19860, T1262, T6685, T14081 all in forward `matches[]` |
| Enmetazobactam guard | T14081, not T1262 |
| Substrate wells | T1005, T1008, T0199, T1213, … **not** in `matches[]` |
| Clavulanate group | T14979 thin ref → canonical T19860 |

Module: `integration/test_forward_screen_coverage.py`.

### Tier 3 — Full library pipeline + timing (CI, tmp_path)

**Library:** full 105-compound `compounds.csv` → `full_library_workspace` fixture.

Offline pipeline integration (`test_forward_full_library_pipeline.py`) plus matching timing benchmarks:

```
reference          match_ms   library_scan_ms
clavulanic acid         …            …
enmetazobactam          …            …
```

**v1 budget (105 compounds, 5 seeds):** total match < 500 ms; per reference < 100 ms.

### Tier 4 — Paperclip integration (manual / nightly)

Requires `PAPERCLIP_API_KEY`. Mark `@pytest.mark.integration`.

| Test | Record | Soft assert |
|------|--------|-------------|
| Batch query 1 | elapsed_ms, result_id | status ok; elapsed < 30 s |
| Clavulanic-specific query | elapsed_ms, result_id | output mentions PMID 40484381 or DOI 10.1016/j.jbc.2025.110347 |
| Cost log | append to `state.forward.literature_searches.metrics[]` | ≤ 6 searches per v1 run |

Do **not** hard-fail cost thresholds until one manual baseline is recorded in this doc.

---

## Proposed test layout

```
ml/agent/tests/
  FORWARD_TEST_PLAN.md          ← this file
  conftest.py                   # path overrides, fixture loaders
  fixtures/
    compounds_clavulanate_subset.csv
    compounds_screen_v3_subset.csv   # 23 IDs from data/screens/1/v3/plate_map.json
    literature_summary_clavulanate.json
    refs/T19860.json
  unit/
    test_forward_name_matching.py
    test_forward_compound_groups.py
    test_forward_curated_refs.py
    test_forward_lit_caps.py
    test_forward_literature_only.py
  integration/
    test_forward_pipeline_offline.py
    test_forward_v1_artifacts.py
    test_forward_literature_only_pipeline.py
    test_forward_screen_coverage.py      # Tier 2.5 — v3 plate subset
    test_forward_full_library_pipeline.py  # Tier 3 — 105-compound pipeline
  benchmark/
    test_forward_match_timing.py
    test_paperclip_clavulanic.py   # @pytest.mark.integration
```

**Dev dependencies (when implementing):** `pytest`, optional `pytest-benchmark`.

---

## Implementation order

1. [x] **Alternate-form grouping** in `forward.py` (Case A cross-refs, Case B literature-only path)
2. [x] **Literature caps** enforced in ref writer + search orchestrator
3. [x] **Tier 1–2 tests** on clavulanic fixture subset
4. [x] **Tier 2.5 screen subset** tests on v3 plate compounds (`compounds_screen_v3_subset.csv`)
5. [x] **v1 artifact contract tests**
6. [x] **Tier 3 full-library pipeline + timing** benchmarks
7. [ ] **Tier 4 Paperclip** — baseline recorded; optional CI/nightly gate on `test_paperclip_clavulanic.py`

---

## Status (2026-07-25)

**Done this session**

| Tier | Scope | Module(s) | Tests |
|------|-------|-----------|-------|
| 1 | Unit — name match, groups, caps, curated refs, literature-only | `tests/unit/test_forward_*.py` | 18 |
| 2 | Offline pipeline — clavulanate 6-compound fixture | `test_forward_pipeline_offline.py`, `test_forward_v1_artifacts.py` | 5 |
| 2.5 | **Screen subset** — 23 IDs from `data/screens/1/v3/plate_map.json` | `test_forward_screen_coverage.py` | 6 |
| 3 | Full library — 105-compound pipeline + `<500 ms` match budget | `test_forward_full_library_pipeline.py`, `test_forward_match_timing.py` | 3 + benchmarks |

Run (from `ml/agent/`):

```bash
PYTHONPATH=. python3 -m pytest tests/ -q --ignore=tests/benchmark/
# 31 passed
```

**What's next (Philip P0 — top priority)**

Live forward pass + Paperclip batch ✓ (2026-07-25). **Screening priors curation blocks discovery plate sign-off.**

1. **Curate inhibitor refs to T19860 quality** — for each forward hit on the v3 plate (T1262, T1631/T6685, T14081, T14979, …):
   - **`assay_recommendations.tem1_nitrocefin.screen_conc_uM`** — project default 50 µM unless literature/solubility says otherwise
   - **`entries[]`** — PMID/DOI, Ki/IC50, assay conditions (Paperclip map + full-text)
   - **`literature_summary.json` → `compound_assay_priors`** — `expected_at_50uM`, role, rationale
2. **Update `pvjthomas/runs/1/v3/selection_rationale.md`** — cite priors per well before sign-off.
3. **Then** promote v3 plate → `data/plate_map_r2.json` (after Round 1 validation passes).

**After P0 (lower priority)**

4. **Tier 4 Paperclip CI** — nightly gate on `test_paperclip_clavulanic.py`.
5. **Synthetic kinetics fixture** — parallel track while waiting for R1 CSV.
6. **GNINA batch** — populate `dock_score`; swap exploration wells.
7. **Reverse + bridge test tiers** — mirror forward pyramid.

---

## Baseline log (fill after first integration run)

| Query | elapsed_ms | result_id | limit | notes |
|-------|------------|-----------|-------|-------|
| TEM-1 beta-lactamase inhibitor IC50 nitrocefin | 2087 | s_299e06c9 | 15 | batch query 1 (2026-07-25) |
| clavulanic acid sulbactam tazobactam … | ~2030 | — | 15 | batch query 2; part of forward_batch (total 4058 ms for 2 queries) |
| TEM-1 clavulanic acid Ki nitrocefin (benchmark) | 1970 | s_143e3578 | 15 | PMID 40484381 / DOI 10.1016/j.jbc.2025.110347 in top-15 |

---

## Related docs

- [`../README.md`](../README.md) — agent run instructions
- [`../../COMPOUND_SELECTION.md`](../../COMPOUND_SELECTION.md) — Steps F1–F4
- [`../../../data/screens/README.md`](../../../data/screens/README.md) — forward v1 versioning
- [`../../../data/compound_literature/refs/README.md`](../../../data/compound_literature/refs/README.md) — ref JSON schema
- [`../../../data/STORAGE.md`](../../../data/STORAGE.md) — git vs local size policy
