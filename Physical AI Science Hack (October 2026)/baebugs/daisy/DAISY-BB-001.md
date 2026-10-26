# DAISY-BB-001 — baebugs specimen segmentation, verified-data training on Kaggle

**Status vocabulary:** PROPOSED / IMPLEMENTED / EXECUTED / OBSERVED_EXPLORATORY / FAILED / NULL / NOT_TESTED.
Nothing in this run is promoted to a production model automatically; the best variant is at most a
`VALIDATION_CANDIDATE` for the next independent experiment.

## Data custody (gate 0, fail closed)
Only datasets with status `VERIFIED` in `daisy/datasets.json` (produced by `baebugs.daisy_data verify`)
are staged. Each Kaggle bundle carries `DAISY_DATASETS.json` and one `DAISY_POINTERS.jsonl` per member
(path, sha256, bytes, role). The notebook recomputes every file hash and every member Merkle root
before any training and stops if any root differs from `DAISY-BB-001.json`.
Not staged: raw GBIF images (pointer manifests only; lineage verified locally), the raw DataONE CSV
(observer PII; a PII-stripped derivative is staged instead), `rejected_pseudo_v1` (negative record).

## Frozen training design
Model `yolo11n-seg.pt` (ultralytics 8.4.188, COCO-pretrained init, sha256 recorded at run time),
seed 2026, deterministic, epochs 15, imgsz 640, batch 16, no hyperparameter search, no early stop.

| run | train | val |
|---|---|---|
| A_synth | synth_1_30_r2, synth_1_30_r3_real, synth_seg | their val |
| B_synth_pseudo | A + pseudo_specimens_r3_real | their val |
| C_all | B + multires_mp_0.3 / mp_1 / mp_3 | their val |
| LODO_synth | C minus synthetic | held-out synthetic val |
| LODO_pseudo | C minus pseudo_specimens_r3_real | held-out pseudo val |
| LODO_multires | C minus multires | held-out multires val |

Exactly 6 runs. Every run is evaluated on every member's val split (mask mAP50-95, mAP50), on the
toy renders at 10 and 20 px/mm (exact silhouette ground truth, TOY models), and on the teacher-check
sets; size error (length / width, orientation-free) against toy truth and ruler truth.

## Known before freeze
- Pseudo labels are YOLOE teacher output, not human annotation: their val split measures agreement
  with the teacher, not truth. Ruler truth exists only for the teacher-check sets.
- multires_* are resamples of pseudo_specimens_r3_real; LODO_multires still sees the same specimens
  at their original resolution, so it tests resolution transfer, not specimen transfer.
- Toy renders are parametric toys; they test geometry and scale, not insect appearance.

## Outputs
`results.json` (per run: train/val members, metrics per eval set, size error, weights sha256,
status), `events.jsonl` + Merkle root, best weights per run. Pulled back to magicBLACKbox, re-hashed,
summary committed with a ledger break point.
