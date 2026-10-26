# DAISY-BB-002 — preregistration (source-domain holdout)

Status: PREREGISTERED (design only). Committed before any 002 data is built or any 002 run starts.
Predecessors (immutable, not edited): DAISY-BB-001, -001a, -001b.
Governance: MSM-PIECEWISE-LAB rules — preregister first, unknown values stay null, model output is
never canonical, every step is hashed as evidence, variance accepted within the declared policy.

## Question
Does a segmenter trained on California-dominant museum photos (pseudo_specimens_r3_real + synthetic)
transfer to photos from other states' collections (AZ, NV, OR), and does adding the other states
help on a state it has never seen?

## Data (built by `baebugs.domain_holdout`, then verified by `baebugs.daisy_data`)
- holdout_az, holdout_nv, holdout_or: GBIF occurrence photos per state, labelled by the same YOLOE
  ruler-scaled teacher as r3 (silver labels + ruler mm truth), split 2/3 train, 1/3 val.
- Exclusions: any photo whose GBIF media id or sha256 is in pseudo_specimens_r3_real, _teacher_check,
  _teacher_check2 or _rejected_pseudo_v1; byte-identical photos across states kept once; undecodable
  photos skipped. Counts recorded in holdout_report.json.
- Known limitation: one physical specimen photographed under two GBIF records is not detected.
- r3 is California-dominant but contains ~156 photos from AZ/NV/OR (by sha); those photos are excluded
  from the holdouts, so no photo is shared, but the "CA-only" run is reported as CA-dominant.

## Runs
| run | train | evaluated on |
|---|---|---|
| CA_dominant | synth x3 + r3 | every member's val split |
| LOSO_az | synth x3 + r3 + holdout_nv + holdout_or (train splits) | every member's val split |
| LOSO_nv | synth x3 + r3 + holdout_az + holdout_or | every member's val split |
| LOSO_or | synth x3 + r3 + holdout_az + holdout_nv | every member's val split |

Settings, gates (G0-G3c) and variance policy inherit DAISY-BB-001b unchanged (deterministic=false,
amp decided by gate G3b, init weights pinned).

## Primary measures (declared now)
1. mask mAP50-95 on each holdout_<state> val split; the held-out state for each LOSO run is primary.
2. Ruler-truth median relative length error on each holdout_<state> (truth_real_val.json).
3. Toy-render size error (unchanged from 001).

## Decision rule
- Transfer gap = CA_dominant on holdout_<s> minus CA_dominant on r3 val.
- "Adding states helps" is SUPPORTED for state s only if LOSO_s beats CA_dominant on holdout_<s> by
  more than the variance policy (map_reproducibility_abs 0.03); otherwise NULL. Report every state,
  including nulls and failures.
- Silver labels: all results are OBSERVED_EXPLORATORY; nothing is promoted beyond VALIDATION_CANDIDATE
  without human-reviewed labels.
