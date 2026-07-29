# Compound literature (git-tracked)

Structured per-compound citations and activity data. **Raw search output** (open repositories and optional Paperclip) stays in [`pvjthomas/local/literature/`](../../../pvjthomas/local/README.md).

Sources recorded in each ref's `entries[]`:

| `source` / backend | Examples |
|--------------------|----------|
| `repository` | Europe PMC, PubMed, ChEMBL, Semantic Scholar, OpenAlex |
| `paperclip` | Full-text map on PMC / bioRxiv / proteins (optional) |
| `manual` | Hand-curated PMID evidence (e.g. T19860) |

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
      "source": "repository",
      "pmid": "40484381",
      "pmcid": "PMC12274840",
      "chembl_id": null,
      "ki_uM": 0.85,
      "ic50_uM": null,
      "assay": "nitrocefin",
      "note": "TEM-1 clavulanic acid Ki from nitrocefin inhibition assay"
    }
  ],
  "raw_local": "pvjthomas/local/literature/T19860/"
}
```

Summaries are referenced from [`compound_dossiers.json`](../../compound_dossiers.json).

See also [`refs/README.md`](refs/README.md) for the ref JSON schema.
