# Media manifest

Everything heavy lives outside this repo. Add a row when you record something.

## Peel footage — `peel_seal`

Bucket: `gs://tacit-teacher-media/media/peel-vids/` (project `tacit-teacher`,
`us-central1`). Vertex AI reads `gs://` URIs directly, so this is both the
archive and the input to `tacit/observe.py`. Access is via project IAM.

`V<n>` ids are what citations use — `[V1@00:37]` in
[`docs/peel-video/`](../docs/peel-video/FINDINGS.md) points here.

| V-id | Object | | Length | What |
|---|---|---|---|---|
| V1 | `IMG_0764.MOV` | good | 84 s | full narrated walkthrough |
| V2 | `IMG_0766.MOV` | good | 39 s | slow even peel |
| V3 | `IMG_0767.MOV` | good | 34 s | mat off without disturbing wells |
| V4 | `IMG_0774.MOV` | good | 47 s | "two forces, one from the side, one against the table" |
| V5 | `IMG_0768.MOV` | **error** | 32 s | too fast → splash |
| V6 | `IMG_0770.MOV` | **error** | 26 s | too fast → cross-contamination |
| V7 | `IMG_0771.MOV` | **error** | 24 s | insufficient upward pressure → mat stays sealed |
| V8 | `IMG_0772.MOV` | **error** | 29 s | plate flips out, contents spill |
| V9 | `IMG_0773.MOV` | **error** | 33 s | mat set face-down → benchtop contamination |

All 1920×1080, 30 fps, recorded 2026-07-25. **No slow-motion footage** — Gemini
samples at a fixed 1 fps, so V5's 3-second splash is covered by roughly three
frames. Film future failure modes in slow motion and record the `time_scale`.

Two duplicate downloads (`IMG_0767(1)`, `IMG_0774(1)`) were removed after MD5
confirmed them byte-identical.

## Everything else

| What | Where | Recorded | By |
|---|---|---|---|
| _(example)_ Robot run 1 — failure | `<link>` | | |
| _(example)_ Robot run 2 — after transfer | `<link>` | | |
