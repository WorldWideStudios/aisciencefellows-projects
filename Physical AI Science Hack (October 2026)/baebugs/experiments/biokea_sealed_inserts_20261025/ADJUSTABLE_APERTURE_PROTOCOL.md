# BioKEA adjustable-aperture cassette · publication evidence protocol

PROJECT: biobitworks/baebugs
STATUS: IMPLEMENTED CAD, source inventory, capture protocol; NOT_TESTED physical sorting.
PARENT: Verified 18-leaf MMR predecessor (append successor, never edit old events).

## Variable aperture (one physical cassette, three indexing positions)
Two laser-cut stainless screens have a shared slotted pattern of nominal
width 3.6 mm. An empty upper screen translates across the fixed lower screen
by 0 / 1.2 / 2.4 mm, yielding 3.6 / 2.4 / 1.2 mm **nominal overlap**.
This is NOT a verified organism passage threshold or qualified wet seal.
Adjust only with no specimen, no water, stationary/de-energized hardware and
an operator approval. Positive mechanical latch and calibration photo are
required before the next separately numbered sample batch.

This sliding-interface design raises serious pinching/bypass risks for legs,
wings and fragments. For high-value or especially fragile specimens, prefer
fixed single-layer plates in the already modeled removable stainless carrier.
Assumed 316L candidate 0.7 mm sheet, carrier dimensions and stops require
vendor DFM, flatness, burr and surface-finish checks. Do not manufacture this
as a validated specimen-contact assembly from CAD alone.

## Per-batch before/after evidence
Intake accession, frozen sample identity and label image -> raw camera image ->
calibration -> independent segmentation candidates -> empty/locked filter ID ->
capture at every retained/passed tray and secondary catch -> edge and gasket
residue check -> human expert decision -> permanent voucher or downstream
DNA/RNA preparation branch. Same image content can occur multiple times but
each acquisition has its own occurrence ID and context.

Never infer that no detections equals complete specimen recovery.
Clumped sample, appendage detachment, identical morphology and overlapping
camera regions can make the identity UNKNOWN. Recovery rate requires
mass balance with uncertainty and actual input and output counts.

## Lab interfaces and evidence states
The module catalog contains alternate arms, trays, cameras, filters, fluids,
heat, reagents and goals. Its source references and risks are NOT hardware
drivers. The xArm7 plate-shuttle implementation, optional LeRobot SO101 docs,
and Partabot rail are not interchangeable without proven interface mapping.

source_inventory.json stores exact-byte SHA256 and repository commit identity
for BioKEA/BugSorter, zlite/entosieve, BioKEA/BugPicker, the GPL-3.0
BugPicker-arm-demo and a pinned LeRobot SO101 reference. These sources are
read-only. Their licenses require independent review before code redistribution.

## LOMO x FCO/FCG
lomo_comparison_plan.json is a deterministic proposed contrast matrix,
one module changed at a time. Every empirical delta is NULL / NOT_COMPUTED
and each comparison is NOT_TESTED. Freeze future measurements, blinding,
source grouping and variance policy BEFORE real data is observed.
Relevant observables:
- Expert adjudicated recall/precision, false unknown/novelty alerts
- Morphology damage per wing/leg/antenna/exoskeleton region
- Fraction retention, bypass, residue, recovered-object uncertainty
- Throughput per expert-verified organism and fractions
- Reagents, water, temperature, preservation and resource attribution
- Molecular outcome only after consent/SOP: DNA and separate RNA quality.

Taxonomic novelty remains a CANDIDATE until expert voucher/taxonomic review
and independent supporting evidence. Pseudo-label mAP is NOT taxonomy truth.

## External scientific context
Birnboim and Doly, NAR 1979, doi:10.1093/nar/7.6.1513 is bacterial plasmid
alkaline lysis, NOT a validated insect whole-body DNA/RNA method. Gravity
filtration is a general fluid-transport technique, not a demonstration of
non-destructive separation of fragile insects. Reagents, heating and
destructive processing require human authorization and independent protocols.

## Operational integrity and tickets
custody_watch.py checks the exact-byte baseline and independent ordered
MMR prefixes on magicPRObox, polling every ~1 second while running.
Mismatch yields CHAIN_BREAK_HOLD and the first divergence. The local
dashboard shows a visible hold; there is NO authenticated operator-approval
writeback, actual camera telemetry, motor control or remote notification.
Preserve predecessor receipts and open a human ticket separately.
A static Vercel snapshot is not a live connection to the local watcher.

## Reproduction
OpenSCAD source: variable_aperture_cassette.scad.
DXF/PNG: output/variable_*.
Tests: python3 -m unittest test_capture_protocol test_variable_aperture -v
Notebook: variable_aperture_repro.ipynb.
Local live read-only server: python3 custody_watch.py serve --port 8786
Evidence endpoint: http://127.0.0.1:8786/api/status
SSE: http://127.0.0.1:8786/api/events

CUTTING DRAWINGS: DFM CONCEPT, NOT FABRICATION RELEASE.
PHYSICAL RECOVERY: NOT_TESTED. MMR: identity/custody, NOT causality/truth.
