# baebugs: requirements and how-to (teammates)

Everything runs from the repo root. Python 3.10-3.12 (3.12 recommended; 3.15 is too new for torch).

## 1. Install

```bash
git clone https://github.com/biobitworks/baebugs && cd baebugs
python3.12 -m venv .venv && source .venv/bin/activate      # or: uv venv -p 3.12
pip install -r requirements.txt                              # core + twin + filters + tests
pip install -e ".[yolo,notebook,dev]"                        # vision models, notebooks
pytest -q                                                    # 40 tests, no GPU or network needed
```

| Need | Packages | For |
|---|---|---|
| core | numpy, opencv-contrib-python-headless, pyyaml, pandas | sizing, sieve plans, twin |
| geometry | trimesh, manifold3d, shapely, mapbox-earcut | toy insects, filter plates, passage twin, tower twin |
| vision | ultralytics 8.4.x, CLIP (git), torch (MPS / CUDA) | YOLO / YOLOE / FastSAM |
| local LLM (optional) | Ollama running locally (qwen3:1.7b, lfm2.5, qwen2.5vl:3b) | model comparison tiers |
| Kaggle (optional) | `kaggle` CLI + `~/.kaggle/kaggle.json` | DAISY GPU training |

Large data never goes in git: on magicstudio it lives on the external drives
(`/Volumes/magicBLACKbox/baebugs` data + runs, `/Volumes/magicLABbox/baebugs` venv + weights).

## 2. The bench: multi-tier tower (what the robot does)

Wood tower: a central post with cantilevered plywood **rail arms** on two faces, levels staggered by half a
pitch. **Storage face** = parked filter trays (overflow in a bench rack); **filter face** = a couple of active
tiers over the catch tray on the lowest level, water from the top. Trays (printed 2x3 frames with side
handles) slide in and out along the rail arms; the Partabot arm on the linear rail moves them, so it can
navigate the whole BioKEA step 1. Metal plates are preferred for dead specimens (rigid, thin, cleanable).

```bash
python -m baebugs.tower_twin demo                    # food-analog spill -> trays to mount -> emulated arm run
python -m baebugs.tower_twin plan --objects objects.jsonl --tiers 2 --out run.json
```

1. Image the first spill (USB/AmScope, ruler or ArUco in view) -> `objects.jsonl` (length_mm, width_mm per object;
   `baebugs-pipeline` or BugPicker's `objects.jsonl` both work).
2. The planner scores every ordered set of available trays (kit + rack) by expected fraction purity over the
   size classes (`config/insects.yaml`), using an ellipsoid passage model (flat / side / end-on silhouettes vs
   the real hole shape). Objects no filter separates confidently -> **VIP** list for a human.
3. The emulator runs the arm program (fetch -> insert coarse->fine top->bottom -> pour -> rinse -> pull each
   tier -> image -> return) and **fails closed** on reach, occupancy, order, missing catch tray or water.
   Each action is a Merkle leaf; the run root identifies the run.

**Measure before trusting times/reach:** every value marked `MEASURE` in `baebugs/config/tower.yaml`
(slot pitch, heights, rail, arm reach, speeds) is a placeholder until the tower is built.
Measure real apertures with `baebugs calibrate-sieve` (one backlit photo per mesh) and update
`config/sieves.yaml`; punch / perforated sizes in the filter library are **nominal**.

## 3. Filters and the passage twin

```bash
python -m baebugs.punch_filters --out print/filters        # 31 hole types: craft punches, canvas, tulle, metal sheet/mesh
python -m baebugs.passage_twin                              # 91 toy insects x every hole, rigid toy vs folded body
```
Finding: round/square/hex holes pass bodies lying flat only below ~0.6-0.7 x the hole diameter; the rest pass
end-on (needs flow to stand them up). Slots cut at 1.0 x slot width lying flat -> width selection without
alignment; this is where hole shape (not size) matters.

## 4. Vision models

```bash
baebugs-pull ...                 # parallel GBIF / Essig pulls (see pull_data.py --help)
baebugs-train ...                # YOLO11n-seg rounds with a ledger callback (commit + push per epoch)
python -m baebugs.model_compare vision --methods classical,yolo,yoloe --ppm 5,10,20
python -m baebugs.model_compare text --models qwen3:1.7b      # local LLM tiers (Ollama)
```

## 5. Toy insects (print) + Merkle KG
`print/fuse1/` = 91 **toy** STLs for Formlabs Fuse 1+ (parametric stand-ins, not replicas; suspect sizes flagged).
`python -m baebugs.insect_kg` rebuilds the per-insect Merkle trees; `python -m baebugs.insect_lomo` runs
LOMO / LOFO / small->large / large->small with the logic -> local model -> Claude -> human cascade.

## 6. DAISY verified-data training on Kaggle
```bash
python -m baebugs.daisy_data verify --out /Volumes/magicBLACKbox/baebugs/daisy --ledger   # hashes, lineage, leakage, PII
python kaggle/freeze_protocol.py --datasets .../daisy/datasets.json                        # refuses unless all VERIFIED
python -m baebugs.daisy_data stage --out .../daisy && kaggle datasets create -p .../kaggle/<bundle> --dir-mode zip
python kaggle/make_daisy_kernel.py && kaggle kernels push -p kaggle/daisy_bb_001
```
Protocol: `daisy/DAISY-BB-001.md`. The notebook re-hashes every file and stops on any mismatch; results are
OBSERVED_EXPLORATORY, nothing is promoted automatically. Raw DataONE CSV (personal data) never leaves the drive.

## 7. Provenance conventions
- Commit + push at every Merkle break point (`ledger/*.jsonl` via `GitLedger`); never rewrite ledger lines.
- Every build ships a Jupyter notebook in `notebooks/` that replays it with swappable data.
- Nominal / placeholder / toy values are labelled as such in data, not just in docs.

## 8. Doctor (stress test, BP5)
```bash
scripts/doctor.sh                         # or: python -m baebugs.doctor [--quick] [--json out.json]
```
Runs pytest, ruff (counts only, no auto-fix), pip check, import of every module, notebook JSON/nbformat-4
parse (not executed), STL watertightness (trimesh), labware JSON, html-validate + axe accessibility on
`dashboard/twin/bench_twin.html` (and `site/` if present), npm/brew doctor, gum, and the `resolve.references` import.
Each check prints PASS / FAIL / SKIP with a reason; SKIP (tool missing) is never counted as a pass. Exit code 1 if any
FAIL. `--quick` skips the heavy checks.

Bring your own check: drop `checks.d/<name>.py` (or point `BAEBUGS_DOCTOR_CHECKS=/some/dir:/other` at a directory)
defining `run()` that returns a detail string. Raise `baebugs.doctor.Skip("reason")` to skip; any other exception is a FAIL.
```python
# checks.d/drive_mounted.py
import os
def run():
    assert os.path.isdir("/Volumes/magicBLACKbox"), "drive not mounted"
    return "drive mounted"
```
