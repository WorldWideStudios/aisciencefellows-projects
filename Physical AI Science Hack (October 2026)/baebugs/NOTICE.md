# NOTICE: what is ours, what is not, and what each thing requires

Records what the licences say; not legal advice. Full per-file view: `docs/CLAIMS.md` (generated) and `site/aok/LICENSE_AUDIT.md`.

## Ours (biobitworks), MIT (`LICENSE`)
Code, notebooks, generated STL/OpenSCAD/DXF prototype parts, Opentrons labware JSON and protocols, pages, protocols and
ledgers, the logo (`assets/brand/`), the demo video and the reel's soundtrack (synthesized in `docs/demo/make_reel.py`).
Bench photos and videos in `assets/` were taken by the team at the event; they show third-party products and are published
re-encoded without metadata; one photo with people's faces is withheld (hash only).

`filtration-robot/` (SO-101 arm + webcam vision) was contributed by teammate lowojoandro through PR #24 with no separate licence file, so it is covered by the repository MIT licence as a contribution; its printable `filter_markers.pdf` is a fiducial marker sheet.

## Used under their own terms (not relicensed)
| Thing | Licence | What it requires here |
|---|---|---|
| Ultralytics YOLO / YOLOE | AGPL-3.0 | any trained weights (none are distributed in this repo) are AGPL-3.0; shipping a model means offering its source under AGPL-3.0 or holding an Ultralytics licence |
| GBIF museum photos | CC0 or CC BY 4.0 per record | CC BY rights holders must be credited wherever images, crops or figures appear; per-record licence and rights holder are in the dataset manifests and `daisy/licences_gbif.json`. No GBIF images are redistributed in this repo |
| OWLv2 (Google) | Apache-2.0 | used as a downloaded model; not redistributed |
| Bricolage Grotesque | SIL Open Font License 1.1 | the wordmark in `assets/brand/*.svg` is outlined from it; OFL permits this. Pages load the font from Google Fonts |
| Opentrons API and labware schema | Apache-2.0 | our labware/protocols follow the schema; "Opentrons" is their trademark, no endorsement implied |
| three.js, trimesh, PyLabRobot | MIT | keep their notices |
| manifold3d | Apache-2.0 | none on generated meshes |
| BioKEA BugPicker, BugPicker-arm-demo | GPL-3.0 | pinned by commit hash only; nothing copied. Tray sizes were measured from their design files, no geometry reused |
| BioKEA BugSorter, PlateReader; zlite repos | no licence (all rights reserved) | pinned by hash only; ask the owners before any reuse |
| Label Studio | Apache-2.0 | used as an external tool; export format only |

## Not established by anything here
Patent novelty, inventorship, manufacturing fitness, biological safety, or redistributable model weights.
