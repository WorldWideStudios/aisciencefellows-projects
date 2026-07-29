# Philip local workspace (not in git)

This tree is **gitignored**. Use it for large or intermediate artifacts. Teammates consume **summaries** from `data/compound_dossiers.json` and `data/assay/`.

Policy: [`data/STORAGE.md`](../../data/STORAGE.md)

## Layout

```
local/
├── literature/{compound_id}/     # raw search dumps (open repos + optional Paperclip map)
├── docking/{compound_id}/        # GNINA .sdf, .pdbqt, logs
├── kinetics/                     # full kinetics_r{n}.csv from plate reader
├── similarity/                   # Tanimoto matrices, cluster debug
└── scratch/                      # notebooks, plots, one-off scripts
```

## After adding local files

1. Curate a summary into `data/compound_dossiers.json` or `data/compound_literature/refs/{id}.json`.
2. Ensure dossier `*_storage` fields point at the local path.

## Bootstrap (optional)

```bash
mkdir -p pvjthomas/local/{literature,docking,kinetics,similarity,scratch}
```

No need to pre-create per-compound folders; add `{compound_id}/` when data exists.
