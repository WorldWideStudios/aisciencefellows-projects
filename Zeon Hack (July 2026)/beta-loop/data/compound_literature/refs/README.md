# Structured compound literature refs (git-tracked)

Curated citations and activity data per compound. **Raw search output** stays in [`pvjthomas/local/literature/`](../../../pvjthomas/local/README.md).

Each ref may include `assay_recommendations.tem1_nitrocefin`:

- `screen_conc_uM` — recommended final assay concentration
- `screen_conc_source` — `literature` | `10x_ic50` | `10x_ki` | `project_default`
- `screen_rationale` — human-readable justification

See [`pvjthomas/COMPOUND_SELECTION.md`](../../../pvjthomas/COMPOUND_SELECTION.md) Step F5 for the concentration rule priority.

## Files

One JSON per compound when populated:

```
refs/T19860.json
refs/T1262.json
…
```

## `{compound_id}.json` shape

```json
{
  "compound_id": "T19860",
  "match": "yes",
  "support": "strong",
  "entries": [
    {
      "source": "paperclip",
      "pmid": null,
      "chembl_id": null,
      "ic50_uM": null,
      "assay": "nitrocefin",
      "note": "classic TEM-1 suicide inhibitor"
    }
  ],
  "raw_local": "pvjthomas/local/literature/T19860/"
}
```

Summaries are referenced from [`compound_dossiers.json`](../../compound_dossiers.json).
