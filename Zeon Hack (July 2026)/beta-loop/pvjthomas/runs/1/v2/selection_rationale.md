# Round 1 / version 2 — validation plate rationale

**Round:** 1 (first closed-loop screen) · **Version:** 2 (`r1-validation-v2`)  
**Supersedes:** `data/screens/1/v1/` (24-compound discovery layout — not run)

See [`data/README.md`](../../../../data/README.md) for rounds vs versions.

---

## Purpose

Minimal assay validation before the full compound screen. Two conditions only:

| Polarity | Wells | Condition | Expected |
|----------|-------|-----------|----------|
| **Negative** | A1–A4 | DMSO vehicle + TEM-1 + nitrocefin | High A490 slope (no inhibition) |
| **Positive** | A5–A8 | Clavulanic acid T19860 @ **50 µM** + TEM-1 + nitrocefin | ≥50% inhibition vs vehicle |

**Pass gate:** mean vehicle slope high · mean clavulanic ≥50% inhibition → assay OK for discovery.

---

## Concentration & literature

| Field | Value |
|-------|-------|
| Final compound conc. | **50 µM** |
| Working solution | 500 µM (5 µL into 50 µL final) |
| Library source | T19860 · PHD215176 **h7** · 10 mM DMSO stock |
| Pre-incubation | 10 min before nitrocefin |
| Read | A490 initial slope |

**Literature basis (git):** [`data/compound_literature/refs/T19860.json`](../../../../data/compound_literature/refs/T19860.json)

- TEM-1 Ki (clavulanic acid) = **0.85 µM** — Radojković et al., *J Biol Chem* 2025, [PMC12274840](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12274840/)
- Literature nitrocefin assay: 0.25 nM TEM-1, 200 µM nitrocefin, 0.25–5 µM inhibitor, 100 mM NaPi pH 6.4, 25 °C, A486
- 50 µM is ~60× Ki → strong inhibition expected at our screen conc.

**Raw Paperclip + full text (local):** `pvjthomas/local/literature/T19860/`

---

## Robot / workflow

- Active plate map: [`data/plate_map_r1.json`](../../../../data/plate_map_r1.json)
- Frozen snapshot: [`data/screens/1/v2/plate_map.json`](../../../../data/screens/1/v2/plate_map.json)
- Protocol: [`pvjthomas/NITROCEFIN_ASSAY.md`](../../../NITROCEFIN_ASSAY.md)
