# BioKEA Track A: OpenSCAD virtual bench + Antigense-style custody lane
This **virtual-only CAD demonstration** executed on magicPRObox with OpenSCAD 2026.10.11.

## Evidence boundaries
- Parent CAD: print/bench/tower.scad and baebugs/config/tower.yaml. All MEASURE dimensions are placeholders.
- tower_three_analogs.scad: schematic wooden post, storage rails, two active filter trays, catch tray and three toy analogs.
- output/tower_preview.png: actual OpenSCAD render.
- output/tower_mesh.stl: actual exported STL. Disjoint bodies are expected; NOT print-ready.
- output/index.html: read-only dashboard with browser SHA-256 and MMR-prefix verification, refreshed every eight seconds.
- output/events.jsonl and prefix-*.json: canonical append-only identity/custody history.
- output/status.json: mutable derived dashboard projection, NOT a canonical receipt.
- cad_build.py: executable/recompute verifier. It refuses to overwrite an existing lane.
- cad_custody_replication.ipynb: human/machine replication.

## Antigense relationship
Construction follows HYDRALAMP_MMR_V1 from biobitworks/antigense-cyberhack/src/custody.py.
The original Antigense function was imported separately on magicPRObox and compared
on the same ordered event inputs. Parent Antigense ledger/root is NOT MODIFIED or
spliced. The relationship is ALGORITHM_DERIVED_FROM, not causality or authorization.

Each event: canonical JSON -> SHA-256 content identity and FCO -> indexed event leaf
-> equal-height peak merging -> left-to-right peak bagging with domain separation ->
recomputed prefix root. Every prefix keeps ordered leaves and peaks.
All records are NOT_SIGNED. Hashes do not certify physical or scientific truth.

## State distinctions
- IMPLEMENTED: CAD design, read-only UI, independent browser verifier.
- EXECUTED / OBSERVED: OpenSCAD render/export and remote host parity checks.
- FAILED: any test failure preserved as a separate successor event.
- NOT_TESTED: actual robot motion, recovery, hydraulic control, measured apertures,
  operator identity, notifications.
- NOT_COMPUTED: sample recovery efficiency, throughput and model accuracy.

## Reproduction
Run from repository root after OpenSCAD installation:
  python3 experiments/biokea_scad_custody_20261025/cad_build.py verify
  python3 -m http.server 8765 --directory experiments/biokea_scad_custody_20261025/output

Do not rerun build in the same folder. Create a successor folder and a fresh
ordered ledger for new experiments. The local HTTP UI can display appended
events; a static Vercel deployment requires a new publish/deploy for updates.

References:
https://github.com/biobitworks/baebugs
https://github.com/biobitworks/antigense-cyberhack

## Successor — DAISY-BB-002a v2 research result
New events 10–13 bind GitHub source SHA-256s, preregistered exploratory
decision, historical lost weights (FAILED) and actual GitHub human review
ticket #2. Event 14 binds the updated local read-only dashboard HTML.

output/training_review_002a.json is a derived source-bound review.
The separate training experiment has 41 event leaves and its own
Merkle root (09b78c8...). The CAD MMR is NOT a cryptographic
extension of that training tree or any Antigense historical MMR.
The physical workcell and model serving remain NOT_TESTED.
The HTML is a published snapshot, not a live Kaggle subscription.
