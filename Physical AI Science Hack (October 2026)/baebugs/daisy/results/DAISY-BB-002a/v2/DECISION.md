# DAISY-BB-002a v2 — decision (preregistered rule, amendment 1)

Kernel biobitworks/baebugs-daisy-bb-002 version 2 (G3c fix, kernels 73dc825). Protocol DAISY-BB-002a sha256 1539b8f8728072e2ffcb911e4997ff6e600c0467a3d3179ce7147e47cd8cbf51.
Events 41, events Merkle root 09b78c8ff6abbbb8a81738ac474807603463c54ee1f98f6825bd9edea176d9bc. Custody: 14/14 members OK.
Gates: G2 init weights pass, G3a environment pass, G3b AMP smoke pass (decision amp=false), G3c: CA_only 16 epochs all finite,
Synth_only 16 epochs all finite. Status of both runs: OBSERVED_EXPLORATORY (silver teacher labels).

## Primary measure: mask mAP50-95 on each held-out state (val split; tolerance 0.03)
| holdout | photos | CA_only | Synth_only | CA - Synth | transfer gap (CA holdout - CA r3_ca val 0.8519) | verdict "real CA photos help" |
|---|---|---|---|---|---|---|
| holdout_az | 72 | 0.8447 | 0.1492 | +0.6955 | -0.0072 | SUPPORTED |
| holdout_nv | 8 | 0.5370 | 0.0393 | +0.4977 | -0.3149 | NOT_INTERPRETED (n<20) |
| holdout_or | 132 | 0.7128 | 0.1923 | +0.5205 | -0.1391 | SUPPORTED |

## Secondary: ruler-truth median relative length error (teacher mm truth)
CA_only: {"teacher_check": 0.3004, "teacher_check2": 0.0306, "r3_ca": 0.0165, "holdout_az": 0.0138, "holdout_nv": 0.021, "holdout_or": 0.0118, "pseudo_specimens_r3_real": 0.0158}
Synth_only: {"teacher_check": 0.9165, "teacher_check2": 0.0443, "r3_ca": 0.0374, "holdout_az": 0.0294, "holdout_nv": 0.1111, "holdout_or": 0.0195, "pseudo_specimens_r3_real": 0.0365}

## Secondary: toy renders (exact parametric truth)
CA_only: {"ppm10": {"n": 91, "detected": 91, "median_rel_len_err": 0.2175, "median_rel_wid_err": 0.1045}, "ppm20": {"n": 91, "detected": 91, "median_rel_len_err": 0.2267, "median_rel_wid_err": 0.126}}
Synth_only: {"ppm10": {"n": 91, "detected": 91, "median_rel_len_err": 0.1362, "median_rel_wid_err": 0.0524}, "ppm20": {"n": 91, "detected": 91, "median_rel_len_err": 0.0941, "median_rel_wid_err": 0.0256}}

## Reading (exploratory, silver labels)
- On AZ and OR, training on real California photos beats synthetic-only by far more than the variance policy: SUPPORTED for both.
- Transfer gap: AZ is within tolerance of the CA val score (-0.0072); OR drops -0.1391,
  so OR photos are measurably harder for a CA-trained model. NV (8 photos) is reported only.
- Toy renders go the other way: Synth_only sizes the printed-toy renders better (median length error 0.0941
  vs 0.2267 at 20 px/mm). Relevant for the physical demo, which uses printed toys.
- teacher_check scores ~0 for both runs (and large ruler error); that eval set behaves unlike the others and needs a look before it is used.
- Labels on every real-photo set come from the same YOLOE teacher, so these numbers measure agreement with the teacher across
  collections, not accuracy against human-reviewed labels. No promotion beyond VALIDATION_CANDIDATE.

## Known loss
The kernel's FINISH step copies best.pt only for runs whose status is EXECUTED, but EVAL relabels runs OBSERVED_EXPLORATORY first,
so both runs' weights were deleted before export. Weight sha256 (realization identity) are recorded:
CA_only 316ce50545855c4076601d9c0f558f7aee4bb98313c97d9131df893a820a8b0a, Synth_only bd036ec7a5dab7e10fd16eb542f82969c8fc0d154775b6193b133e33da42064c.
Fixed in the kernel generator after this run; the 001b v6 re-run (pushed before the fix) has the same defect.
