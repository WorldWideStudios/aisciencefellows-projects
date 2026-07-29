# Deprecated — Run 3 v2

**Folder:** `data/screens/3/v2-deprecated/` (renamed so teammates do not pick this layout by mistake)  
**Status:** deprecated (2026-07-26)  
**Do not use for robot scheduling or sign-off.**

Run 3 **v1** (`data/screens/3/v1/`) is the active plate-design revision. v2 was an alternate 6-compound layout (cut expected ± hits, add T1005 + T0198) that is **not** proceeding.

Artifacts in this directory are kept for history only:

- `compound_list.json` / `.csv`
- `plate_map.json` / PNGs
- `manifest.json`

Regenerating v2 is discouraged:

```bash
# avoid — v2 is frozen deprecated
# python ml/scripts/build_screen3.py --version 2
```

See [`pvjthomas/runs/3/v2/selection_rationale.md`](../../../pvjthomas/runs/3/v2/selection_rationale.md) for the original design intent.
