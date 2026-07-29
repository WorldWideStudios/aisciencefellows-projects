# Compound library

**Source:** [TargetMol Beta-Lactam Compound Library-A (Google Sheets)](https://docs.google.com/spreadsheets/d/1b7UuzXu_auqoq2hFT81X3UuRutxxWxZW/edit?gid=372192752#gid=372192752)

**Local file:** `compounds.csv` (105 compounds, synced from sheet gid `372192752`)

**Per-compound support:** [`compound_dossiers.json`](compound_dossiers.json) — summaries in git; raw literature/docking/kinetics under [`pvjthomas/local/`](../pvjthomas/local/README.md). See [`STORAGE.md`](STORAGE.md).

## Format

| Column | Description |
|--------|-------------|
| `compound_id` | TargetMol ID (e.g. T19860) |
| `plate` | Source plate ID (PHD215176 / PHD215177 / PHD215178) |
| `row`, `col` | Well on source plate (lowercase row letter) |
| `concentration_mM` | 10 mM stock in DMSO |
| `volume_ul` | 50 µL |
| `smiles` | From TargetMol sheet |
| `scaffold_class` | `inhibitor` \| `antibiotic_substrate` \| `exclude` \| `other_β_lactam` \| `artifact_suspect` (_stub_) |
| `functional_class` | _stub_ — see [COMPOUND_SELECTION.md § Suggested mapping](../pvjthomas/COMPOUND_SELECTION.md#suggested-mapping--unified-functional-classes) |
| `tier` | 1 = known inhibitor, 3 = substrate control, blank = TBD |
| `exclude` | `true` for nitrocefin (T19709) only |

## Re-export from Google Sheets

```bash
curl -fsSL "https://docs.google.com/spreadsheets/d/1b7UuzXu_auqoq2hFT81X3UuRutxxWxZW/export?format=csv&gid=372192752" \
  -o /tmp/compound_lib.csv
# then re-run parse script in pvjthomas/COMPOUND_SELECTION.md or project tooling
```

## Related files

| File | Purpose |
|------|---------|
| [`compound_dossiers.json`](compound_dossiers.json) | Per-compound summaries (literature, docking, assay pointers) |
| [`assay/run_{n}_summary.json`](assay/README.md) | Final screen results per run |
| [`compound_literature/refs/{id}.json`](compound_literature/refs/README.md) | Curated citations (when populated) |
| [`STORAGE.md`](STORAGE.md) | Git vs local policy |

## Selection plan

See [pvjthomas/COMPOUND_SELECTION.md](../pvjthomas/COMPOUND_SELECTION.md).
