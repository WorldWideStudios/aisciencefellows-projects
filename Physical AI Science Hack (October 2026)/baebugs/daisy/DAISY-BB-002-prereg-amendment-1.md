# DAISY-BB-002 — preregistration amendment 1 (before any 002 data was built or run)

The original preregistration (`DAISY-BB-002-prereg.md`) is unchanged. This amendment is committed
before the amended data is built and before any 002 run.

## Evidence that forced the change (observed 2026-10-25 ~07:20 UTC)
`baebugs.domain_holdout` admitted 2,514 AZ / 1,229 NV / 2,792 OR photos not already used, but the
YOLOE ruler-scaled teacher kept none of AZ. A 40-photo sample per state (work/teacher_diag.log):

| state | undecodable | no ruler | ruler but no 1–30 mm object | kept |
|---|---|---|---|---|
| AZ | 6 | 27 | 7 | 0 |
| NV | 0 | 34 | 5 | 1 |
| OR | 0 | 34 | 6 | 0 |

Most remaining photos have no ruler (not pinned-specimen-on-stage photos). The out-of-state photos that
do have rulers were already labelled into pseudo_specimens_r3_real (about 156 by sha). So
holdout_<state> built from new photos is NOT_BUILT for all three states.

## Amended data
Split pseudo_specimens_r3_real by the photo's source collection (filename present in gbif_<state>/images,
confirmed by sha256), keeping its teacher labels and ruler truth unchanged:
- r3_ca: photos from gbif_ca_2 / gbif_specimen_images (train and val splits as in r3).
- holdout_az, holdout_nv, holdout_or: r3 photos sourced from that state; every photo goes to val.
Photos whose source cannot be resolved are dropped and counted. No photo is in more than one set.

## Amended runs (multires sets excluded: they are resamples of all of r3, including out-of-state photos)
| run | train | evaluated on |
|---|---|---|
| CA_only | synth x3 + r3_ca | every member's val split |
| Synth_only | synth x3 | every member's val split |

LOSO runs are dropped: per-state sets are too small to train on (NV is expected to be single digits).

## Measures and decision rule (replacing the original's)
1. mask mAP50-95 and ruler-truth median relative length error on holdout_az, holdout_nv, holdout_or
   (each reported separately with its n; NV reported but not interpreted if n < 20).
2. Transfer gap = CA_only on holdout_<s> minus CA_only on r3_ca val.
3. "Real CA photos help on other states" is SUPPORTED for state s only if CA_only beats Synth_only on
   holdout_<s> by more than map_reproducibility_abs (0.03); otherwise NULL.
All results remain OBSERVED_EXPLORATORY (silver labels); no promotion without human-reviewed labels.
