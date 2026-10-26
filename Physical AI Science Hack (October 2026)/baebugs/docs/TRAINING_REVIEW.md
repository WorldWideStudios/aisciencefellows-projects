# Training review for the PI (baebugs, Oct 25 2026)

What was trained, what it showed, how sure we can be, and where the evidence is. Every claim below points to a file
in this repo; numbers are copied from those files, not restated from memory. Status words follow the DAISY protocols:
results are **OBSERVED_EXPLORATORY** (silver labels from a teacher model, not human-reviewed) unless stated.

## Wins

| # | What | Result | Strength | Evidence |
|---|---|---|---|---|
| 1 | **Real California photos beat synthetic-only training on other states** (DAISY-BB-002a v2, segmentation, mask mAP50-95) | AZ: 0.845 vs 0.149 (+0.696, n=72). OR: 0.713 vs 0.192 (+0.521, n=132). NV n=8, not interpreted | Preregistered rule, amendment 1 → **SUPPORTED** for AZ and OR. Silver labels (same YOLOE teacher), so this measures agreement with the teacher across collections | `daisy/results/DAISY-BB-002a/v2/DECISION.md` |
| 2 | **The CA model transfers to AZ almost without loss** | AZ 0.845 vs CA val 0.852 (gap −0.007); OR drops −0.139 | Same run, same caveat | same file |
| 3 | **Size measurement from the model is within a few percent** on held-out states | Median relative length error vs ruler truth: AZ 1.4%, OR 1.2%, NV 2.1% (CA_only) | Ruler-scaled teacher truth, not calipers | same file |
| 4 | **An insect-ORDER preprocessor works outside California** (DAISY-BB-004 v4, yolo11n-cls, 15 epochs, MPS) | Test (AZ/NV/OR) macro-F1 0.700 vs majority baseline 0.135 → +0.565, top-1 0.948 | Preregistered rule (margin 0.10) → **USEFUL**. Caveats in the addendum: 5 classes in test (no Diptera), Hemiptera n=2 | `daisy/results/DAISY-BB-004/v4/DECISION.md`, `ADDENDUM.md` |
| 5 | **Custody held for every weight that matters now** | All 3 DAISY-004 weights resolve to stored bytes (tensor sha recorded per epoch); 104 hash-chained events | Structural check (`baebugs.resolve`), re-run independently | `daisy/results/DAISY-BB-004/v4/ADDENDUM.md` |
| 6 | **Escalation ladder routes by novelty and verifies picks by hash** (toy demo) | The two most novel toys skipped the taxon models (aphid-like 1.5 mm went straight to the human queue); both picks verified by a single Merkle break box around the toy, no model involved | Demo on rendered toys, 12 specimens, 18 records; statistics recompute from the chain (same hash on rerun) | `docs/ladder_demo/README.md`, `notebooks/tiers_ladder_markov.ipynb` |
| 7 | **Better zero-shot detector for bench assets chosen by evidence** | OWLv2 image-level F1 0.51 vs YOLOE 0.24 against the asset registry (19 photos) | Weak check (object kinds per photo, no boxes yet); boxes stay INFERRED until confirmed | `assets/detector_eval.json`, `docs/RESEARCH_TOOLS.md` |

## Negative and null results (kept, not hidden)

| What | Result | Meaning |
|---|---|---|
| FAMILY_Hymenoptera preprocessor (DAISY-004) | val 0.883 → test 0.167 vs 0.068 baseline (+0.099, under the 0.10 margin) → **NULL** | does not transfer out of California; in the ladder it may only advise, CA-only |
| FAMILY_Diptera | no Diptera in any test split | **undecided** under the frozen rule |
| Toy renders (002a) | Synth_only sizes the printed-toy renders better than CA_only (0.094 vs 0.227 median length error at 20 px/mm) | real-photo training does not help on renders; the physical demo uses printed toys |
| ORDER model on toy renders (ladder demo) | 6 approvals, only 2 correct (both ladybirds); 4 wrong across 3 toys (e.g. Bombyliidae → Hymenoptera at 0.97) | confidence alone is not a safe gate; needs a photo-vs-render domain check + calibration before the rung may decide |
| Local VLM rung (qwen2.5vl:3b) | confidence 0.9 every time, mostly HOLD | uncalibrated; advisory only |
| teacher_check eval set | ~0 for both 002a runs | that eval set is anomalous; not used for decisions |

## Custody breaks (recorded, not repaired)

8 weight hashes are referenced but their bytes were never stored: DAISY-BB-001b v6 (6 runs) and DAISY-BB-002a v2 (2 runs).
Cause: the kernel exported weights only for status EXECUTED after evaluation relabelled runs; fixed (weights saved and
verified right after training, fail-closed custody check). Each break is a `custody_break` event in `daisy/impact_mmr.jsonl`.
Consequence: the 002a numbers above stand as recorded observations, but those two models cannot be re-run or re-scored;
a rerun with the fixed kernel would restore them as evidence.

## Process deviations on DAISY-BB-004 (all filed as amendments before any result was read)

1. Kaggle weekly GPU quota used up → identical kernel code run on magicstudio (amendment 1).
2. CPU too slow (≈4.5 h) → Apple GPU (MPS) (amendment 2).
3. Values-gate defect stopped training after 1 epoch in attempts v2 and v3 (cause: Ultralytics 8.4 keeps the loss as a dict);
   fixed, both attempts kept as invalid evidence (amendments 3–4). v4 is the valid run. Protocol sha256 unchanged throughout.

## What the PI may want to decide

- Promote 002a / 004 beyond VALIDATION_CANDIDATE? Both rest on silver (teacher) labels; a small human-reviewed test set would settle it.
- Rerun 002a and 001b with the fixed kernel to close the 8 custody breaks (needs GPU: Kaggle quota resets weekly, or MPS locally).
- Retrain FAMILY_Hymenoptera with out-of-state photos, and add a Diptera test split.
- Photograph the printed PA12 toys (now depowdered) on a tray with a ruler: first real-photo test set for the toy lane and the domain check.
- Confirm the OWLv2 bench boxes in Label Studio (≈20–30 min) to start a labware detector.

## Reproduce

Every run's protocol, events (hash-chained), results and weights sha are in `daisy/`; weights live on the magicBLACKbox drive
and resolve by hash (`python -m baebugs.resolve`). The MVP graph (`site/mvp/`) lists every file with its hash, claim and licence;
`baebugs-graph get root` gives the same root from the CLI, MCP and npx.
