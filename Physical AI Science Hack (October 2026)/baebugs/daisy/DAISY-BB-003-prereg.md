# DAISY-BB-003 — preregistration (modules as training steps)

Status: PREREGISTERED (design only). No 003 data exists yet; each step below runs only after its
module produces data that passes `baebugs.daisy_data` verification. Predecessors stay immutable:
DAISY-BB-001/001a/001b (6-run ladder; 001b v6 re-run in progress), DAISY-BB-002/002a (002a v2 result:
real CA photos beat synthetic-only on AZ +0.696 and OR +0.521 mask mAP50-95; synthetic-only sized
printed toys better). Governance as before: preregister first, protocol frozen with dataset Merkle
roots, per-run byte + media-id leakage gate, G0-G3c gates, variance policy, weights exported
(FINISH fix f8f0a3f), every step an MMR event. Silver labels stay OBSERVED_EXPLORATORY.

## Principle: the hardware labels the data
Each physical module separates on one property, so its output is a label nobody had to draw:
| module (labbox id) | data it produces | free label | camera scale |
|---|---|---|---|
| bugsorter_trommel / flex_mini_trommel | top-down photo of each bin | size class (zone aperture) | ArUco tag in bin pocket |
| variable_aperture | photo per width step | retained at width w = 2nd dim >= w (square mode) | measured-aperture gate |
| density bath / elutriation (twin stages) | photo of float vs sink, overflow vs underflow | density / settling class | tag on vessel |
| flex_sieve_adapter (Heater-Shaker) | photo of each ring after gentle shake | ring = size class, dispersed for counting | ring diameter (50 mm) |
| handoff_carrier + picker | one photo per picked specimen + well id | identity link specimen -> well | tag on carrier |
| vision_gate + entomologist | expert-confirmed novel classes | class label (attested, hashed) | - |
| printed toys (insect KG) | photos of printed toys in the same trays | exact geometry (toy KG hash) | tag |

## Steps (each = one frozen protocol 003-Sk, run on Kaggle when its data is VERIFIED)
- **003-S1 sieve-labelled size.** Train/evaluate size-class prediction on trommel-bin photos; label =
  bin. Primary: per-class accuracy and median length error vs ArUco scale; compare the 002a CA_only and
  Synth_only weights as initialisations. Decision: sieve labels SUPPORTED as weak supervision if
  fine-tuning beats both initialisations by > 0.03 on held-out bins, else NULL.
- **003-S2 printed-toy bridge.** Photos of printed toys in the trays (exact truth from the toy KG).
  Primary: median relative length error. Tests the 002a finding (synthetic-only better on toys) on real
  photos of toys instead of renders.
- **003-S3 novelty.** Expert-confirmed novel classes (attested labels) as a held-out set. Primary:
  novelty recall and false-novel rate of the vision gate before vs after the update.
- **003-S4 leave one module's data out.** Retrain without each module's data in turn; the drop on the
  shared held-out set is that module's training value (the data counterpart of labbox LOMO).
- **003-S5 Flex deck.** Same as S1 on photos from the Flex sieve adapter, held out by platform
  (bench-trained -> Flex-evaluated), to measure the platform domain gap.

## What is not claimed
No module has produced data yet; all modules are CONCEPT or SIMULATED in `daisy/labbox.json`. Step order
follows data availability, not this list. Any change to a step is a new amendment file before its data
is built.
