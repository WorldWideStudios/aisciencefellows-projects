# Pareto refactor — two-objective + lab-derived multipliers

Status: **planned, not yet executed**. This doc is the handoff spec.

## Objective

Replace the current single `hypothesis_score` (which coupled X and Y —
confidence was baked into the score itself) with **two genuinely
orthogonal objectives**:

- **Hypothesis strength** — how well-supported is this mechanistic
  hypothesis for this patient
- **Hypothesis strong fit for AAV** — how deliverable is this
  hypothesis as an AAV therapeutic

Both objectives incorporate the patient's actual clinical labs, so the
same generic (mechanism × pathway × cell-type) hypothesis lands at
different (strength, aav) coordinates for different patients.

## Axes

- **X = "Hypothesis strength"** (`hypothesis_strength`, 0..~1.2)
- **Y = "Hypothesis strong fit for AAV"** (`aav_viability`, 0..~1)

Both are maximised → ideal hypothesis sits top-right.

## Formulas

### Objective 1 — Hypothesis strength

```
strength = weighted_fit × cross_lab_consistency_bonus + confidence
```

| Term | Source | Notes |
|---|---|---|
| `weighted_fit` | existing | Σ (severity × min(|z|, Z_CAP)) / Σ (severity × Z_CAP). Continuous 0..1. |
| `cross_lab_consistency_bonus` | new | 1.20 if CK z>2 AND aldolase z>2 AND LDH z>2; else 1.00. |
| `confidence` | existing | 0.4·pLDDT_norm + 0.4·log_pw_size_norm + 0.2·depth_norm. Continuous 0..1. |

### Objective 2 — AAV viability

```
aav_viability = tissue_delivery × payload_fit × dgc_rescue
              × precedent_prior × tissue_target_boost × rescue_window
```

| Term | Source | Values |
|---|---|---|
| `tissue_delivery` | existing (`TISSUE_DELIVERY` dict) | skeletal_muscle=0.95, heart=0.75, retina=0.90, cns=0.35, kidney=0.35, ... |
| `payload_fit` | **new**, per mechanism | H01=0.10 (full DMD 11kb, too big), H02=0.90 (in-frame → micro-dys fits), H03=0.60 (AAV-ASO), H04=0.75 (small distal isoforms) |
| `dgc_rescue` | derived from existing | `pathway_dgc_coverage × cell_dgc_completeness` |
| `precedent_prior` | **new**, per (mech, tissue, exon) | 0.95 if FDA-approved skip (45/51/53) on H01/H02; 0.75 if H02+muscle (delandistrogene precedent); 0.60 if H03+PTC (ataluren precedent); else 0.30 |
| `tissue_target_boost` | **new**, per (patient, tissue) | 1.2× heart if LVEF↓ / NT-proBNP↑ / LGE+; 1.2× muscle if FVC↓ / PCF↓; 0.7× CNS if IQ↓; 1.3× retina if ERG abn; 0.7× kidney if UACR↑; else 1.0 |
| `rescue_window` | **new**, per (patient, tissue) | muscle = `1 − MRI_ff/100`; cardiac = `LVEF/60`; else 1.0 |

## Files to modify

### 1. `prototype/ingest/bake_hypothesis_frontier.py`

**Add constants (top of file, near existing dicts):**

```python
PAYLOAD_FIT = {"01": 0.10, "02": 0.90, "03": 0.60, "04": 0.75}

# precedent_prior: keyed by (mech_id, tissue, exon_matches_fda_skip)
# See score_precedent_prior() for the rules.

TISSUE_TARGET_LAB_RULES = {
    # tissue: [(lab_key, direction, threshold_z, boost_factor), ...]
    "heart":           [("LVEF", "low", 2.0, 1.2), ("NT_proBNP", "high", 2.0, 1.2), ("LGE_present", "flag", None, 1.2)],
    "skeletal_muscle": [("FVC_pct", "low", 2.0, 1.2), ("PCF", "low", 2.0, 1.2)],
    "cns":             [("IQ", "low", 2.0, 0.7)],
    "retina":          [("ERG_bwave", "abn", None, 1.3)],
    "kidney":          [("UACR", "high", 2.0, 0.7)],
}
```

**Add helpers:**

```python
def load_patient_labs_raw(conn, cohort, patient_id) -> dict[str, float]:
    """Load raw lab values + z-scores + presence-flags for one patient.
    Returns {lab_key: {value, z, present_flag}}. Used by lab-multiplier fns."""

def cross_lab_consistency_bonus(labs: dict) -> float:
    """1.20 if CK z>2 AND aldolase z>2 AND LDH z>2; else 1.00."""

def tissue_target_boost(labs: dict, tissue: str) -> float:
    """Look up TISSUE_TARGET_LAB_RULES[tissue], multiply active boosts.
    Multiple active rules multiply (heart: LVEF↓ AND LGE+ → 1.2 × 1.2 = 1.44)."""

def rescue_window(labs: dict, tissue: str) -> float:
    """muscle: 1 − MRI_ff/100 (clip [0,1]);
       cardiac: LVEF/60 (clip [0,1]);
       else: 1.0"""

def score_precedent_prior(mech_id: str, tissue: str, exon: int | None) -> float:
    """FDA_APPROVED_SKIPS ∩ H01/H02 → 0.95;
       H02 + muscle → 0.75; H03 + nonsense/splice → 0.60; else 0.30."""

def score_hypothesis_strength(wfit: float, conf: float, xlab_bonus: float) -> float:
    return wfit * xlab_bonus + conf

def score_aav_viability(mech_id, tissue, exon, dgc_pw, dgc_cell,
                        tissue_boost, rescue_win) -> float:
    return (TISSUE_DELIVERY.get(tissue, 0.30)
            * PAYLOAD_FIT.get(mech_id, 0.30)
            * dgc_pw * dgc_cell
            * score_precedent_prior(mech_id, tissue, exon)
            * tissue_boost
            * rescue_win)
```

**Schema changes:**

```sql
-- Add two columns (existing ones retained for back-compat):
hypothesis_strength  REAL,
aav_viability        REAL,
```

Drop table before rebake so new schema takes: `DROP TABLE IF EXISTS hypothesis_frontier;`

**Driver-loop changes (around line 520-540):**

```python
# Load per-patient lab dict once, outside the inner loops:
for p in patients:
    k = (p["cohort"], p["patient_id"])
    labs_raw = load_patient_labs_raw(conn, p["cohort"], p["patient_id"])
    xlab_bonus = cross_lab_consistency_bonus(labs_raw)
    # ... existing wfit, reach, conf computation ...
    strength = score_hypothesis_strength(wfit, conf, xlab_bonus)
    t_boost = tissue_target_boost(labs_raw, cell["tissue"])
    r_win   = rescue_window(labs_raw, cell["tissue"])
    aav_v   = score_aav_viability(mech_id, cell["tissue"], p["exon_n"],
                                   pw["coverage"], cell["dgc_completeness"],
                                   t_boost, r_win)
    # row dict gets:
    row["hypothesis_strength"] = round(strength, 6)
    row["aav_viability"]       = round(aav_v, 6)
```

**Swap Pareto axes:**

```python
keep_v = pareto_flags(patient_rows, ("hypothesis_strength", "aav_viability"))
# ...
keep_g = pareto_flags(all_rows,     ("hypothesis_strength", "aav_viability"))
```

### 2. `prototype/ingest/hydrate_frontier_view.py`

- Add `hypothesis_strength, aav_viability` to the `SELECT` at line 25
- Append two entries to the slim row list (positions 21, 22):
  ```python
  round(r["hypothesis_strength"] or 0.0, 6),
  round(r["aav_viability"] or 0.0, 6),
  ```
- Add to `row_fields` metadata:
  ```python
  "hypothesis_strength", "aav_viability",
  ```

### 3. `workbench/patient_chat.html`

- **`frontierExpand()`** — extend the mapping to pluck `hypothesis_strength` and `aav_viability` from indices 21, 22
- **`frontierComputePareto()`** — change sort/sweep axes from `(hypothesis_score, confidence)` to `(hypothesis_strength, aav_viability)`
- **`frontierSvg()`**:
  - X-axis label → **"Hypothesis strong fit for AAV"**
  - Y-axis label → **"Hypothesis strength"**
  - Auto-scale on both axes (already implemented)
  - Update corner annotations (top-right green: "ideal — strong hypothesis + AAV-tractable"; bottom-left red: "weak evidence + poor delivery"; etc.)
- **Hover tooltip** — replace `score=/confidence=` lines with:
  ```
  strength=0.847  ·  aav_viability=0.312
    fit=0.63 × xlab_bonus=1.20 + conf=0.47
    delivery=0.95 × payload=0.90 × dgc=0.42 × precedent=0.75 × t_boost=1.20 × rescue=0.65
  ```
- **Keep unchanged**: patient-colored dots, green frontier hull, per-patient Pareto filter, curated-set gold ring overlay

## Execution checklist

- [ ] **1.** Add constants (`PAYLOAD_FIT`, `TISSUE_TARGET_LAB_RULES`) to bake
- [ ] **2.** Add helpers (`load_patient_labs_raw`, `cross_lab_consistency_bonus`, `tissue_target_boost`, `rescue_window`, `score_precedent_prior`)
- [ ] **3.** Add scoring fns (`score_hypothesis_strength`, `score_aav_viability`)
- [ ] **4.** Add `hypothesis_strength REAL, aav_viability REAL` to SCHEMA; add `DROP TABLE IF EXISTS hypothesis_frontier;` before create
- [ ] **5.** Populate new columns in per-row dict; wire lab loading outside inner loops
- [ ] **6.** Swap `pareto_flags` axis args to `("hypothesis_strength", "aav_viability")`
- [ ] **7.** Run bake → verify: distinct `(strength, aav)` tuples ≥ 500; H01 rows mostly low-aav; P2 vs P5 muscle-AAV differ
- [ ] **8.** Extend hydrate SELECT + slim rows + row_fields
- [ ] **9.** Run hydrate → verify JSON size ≤ ~2MB
- [ ] **10.** Update `frontierExpand` to pluck new fields
- [ ] **11.** Swap axes in `frontierComputePareto` + `frontierSvg` (X=aav, Y=strength)
- [ ] **12.** Update axis labels, corner annotations, hover tooltip
- [ ] **13.** Reload workbench → verify: per-patient AAV variation visible; frontier is a real staircase; patient colors still work

## Verification criteria

- **No bands**: ≥500 distinct (strength, aav) tuples across 16k rows (currently score has 2083 unique values — expect similar or better for the new axes independently)
- **Per-patient variation**: same (mech × pathway × cell) triple must have different `aav_viability` for two patients with different labs (e.g., P2 with MRI_ff=35% vs P5 with different MRI_ff → different muscle-AAV scores)
- **Sanity checks**:
  - H01 rows (full DMD gene) should cluster on the LOW-AAV side (payload_fit=0.10)
  - H02 + muscle + FDA-skip patient should cluster HIGH on both axes
  - CNS-targeting rows should cluster LOW on AAV (BBB barrier)
- **Frontier shape**: monotonically decreasing staircase, not a cluster

## Known gaps / punts

- `payload_fit` values are engineering-informed guesses, not curated from a payload-size table. Fine for v0; add `aav_capsid_payload.tsv` later.
- `cross_lab_consistency_bonus` only rewards CK/aldolase/LDH co-elevation. Extend to other correlated triples if needed.
- Missing labs (patient never measured UACR) currently treated same as "measured normal" in `weighted_fit`. Flagged as follow-up; not fixed in this refactor.
- `precedent_prior` is a lookup, not a real regulatory database. Manual maintenance until wired to ClinicalTrials.gov.
- `hypothesis_score` column retained for back-compat during rollout; can be dropped once viz is confirmed working.
