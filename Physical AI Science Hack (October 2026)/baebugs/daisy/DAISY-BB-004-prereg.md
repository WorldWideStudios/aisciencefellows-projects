# DAISY-BB-004 — preregistration (per-taxon preprocessors)

Status: PREREGISTERED (design only), committed before the 004 crop dataset is built.
Predecessors immutable: 001/001a/001b, 002/002a (custody breaks recorded for 002a v2 weights), 003 (prereg only).

## Question
Can small specimen-crop classifiers act as preprocessors that route a specimen to its order, and
within an order to its family, so lower / local models only see the taxa they are specialised for?

## Data (built by `baebugs.taxon_crops`, verified, pinned by Merkle root before training)
- Crops of every specimen segmented by the YOLOE teacher in r3_ca (CA) and holdout_az/nv/or, cut from the
  pseudo-label polygon bounding box with 8% padding.
- Label = GBIF taxonomy of the source photo (`order`, `family` from the gbif manifests, matched by media id).
- Split follows the source photo: r3_ca train -> train, r3_ca val -> val, holdouts -> test (out-of-state).
  A photo's crops never span splits (media-id leakage gate = 0).
- Classes with fewer than 20 train crops are pooled as "other" for that level.
- Licences: each crop inherits its source photo's licence (CC0 / CC BY / CC BY-NC) and rights holder;
  the dataset manifest carries them per crop.

## Runs (yolo11n-cls, imgsz 224, 15 epochs, settings/gates/variance from 001b; deterministic=false)
| run | classes | train | eval |
|---|---|---|---|
| ORDER | orders (+other) | r3_ca train crops | r3_ca val, holdout test |
| FAMILY_<order> | families within that order (+other), for the 2 orders with the most train crops | crops of that order | same splits |

## Custody (new, mandatory)
Weights saved and verified right after each run; every checkpoint hashed (file + canonical tensor hash);
fail-closed custody_check before results.json; every weights hash must resolve in the store (resolvability
invariant), otherwise the run is CUSTODY_BROKEN.

## Measures and decision rule
Top-1 accuracy and macro-F1 on val and on the out-of-state test. A preprocessor is USEFUL for a level if its
test macro-F1 beats the majority-class baseline by more than 0.10; otherwise NULL. Silver taxonomy (GBIF
identifications), so results are OBSERVED_EXPLORATORY.
