# MVP audit against Byron's list (2026-10-25)

| Ask | Status | Where |
|---|---|---|
| Interchangeable filters | Found | `print/filters/` (32 hole types on one 50 mm plate, 31 STL, 32 SCAD), `baebugs/punch_filters.py` |
| Modified filtration, plastic vs metal, for the robot | Found (proof of concept, uncalibrated) | Plastic: punched PET/acetate, canvas, tulle, printed PA12. Metal: 12 stainless options + `baebugs/variable_aperture.py` 316L slot stage. Arm that swaps filters is only in open PR #24 (outside fork, unreviewed). |
| Transformed data workflow with chain of custody | Found | `site/mvp/mvp.json` root, MMR logs in `daisy/*_mmr.jsonl`, BREAKs recorded |
| Computer vision at each step | Thin | `baebugs/camera.py`, `docs/toy_photo_models/` (YOLOE, OWLv2, ORDER classifier, local VLM on 2 real toy photos). Gates `G_measured`/`G_capture` are designed; no hardware run at each station yet. |
| Multiple local models with Python preprocessing | Found | `baebugs/taxon_crops.py` (2,627 crops, split by photo), `baebugs/train.py`, `baebugs/local_vlm.py`, DAISY-BB-004 v4 results |
| Toy printing | Found | `print/fuse1/` (91 PA12 toys, manifest, SCAD twins) |
| Scientific objects for remixing | Found | `print/labware/` (8 MIT remixes, Opentrons defs, Merkle) |
| STL to OpenSCAD available | Found | `baebugs/scad_export.py`, `print/*/scad/` |
| One elegant step-by-step flow with music | Was missing; added | `site/story/` (this PR) |

The story page reads every number from the files above and lists each file with its sha256.
Music is synthesised in the browser by the page's own Web Audio code (no audio files, released CC0), off by default.
