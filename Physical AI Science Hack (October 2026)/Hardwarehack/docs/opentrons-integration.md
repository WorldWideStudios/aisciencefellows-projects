# Opentrons integration: what exists, what we tested, what to build

Written Saturday 2026-10-24 about 16:45 PDT, after reading the `ebrinz` branch (11 commits, 16:05 to 16:24 PDT) and running its generated protocol through the Opentrons 10.1.0 simulator. Nothing here changes code. It is the plan and the evidence for the team.

## 1. What `ebrinz` pushed (branch `ebrinz`, not merged to `main`)

| Piece | File | What it does |
|---|---|---|
| Protocol generator | `drug-screen-platform/src/protocol_generator.py` | Plan to a self-contained Flex protocol (apiLevel 2.30) with the transfer list embedded, deck constants at the top, a tube map, and `capture_image` before and after |
| Robot client | `src/flex_client.py` | `FlexClient` over HTTP (health, upload protocol, create run, play/pause/stop, run status, wait, camera snapshot) and `MockFlexClient` |
| Simulator wrapper | `src/simulation.py` | Runs `opentrons.simulate.simulate` and returns ok, steps, log, error |
| Run store | `src/run_store.py` | `runs/<plate>/` with layout, transfers, protocol, snapshots, run info |
| CLIs | `cli/plate.py`, `cli/flex.py` | `plate check/plan/protocol/simulate`, `flex health/snapshot/run/status/pause/stop/demo` (`--mock` for a pretend robot) |
| API | `api/` (FastAPI, loopback only, host and cross-site checks) | layouts, plan, protocol, robot health/snapshot/runs |
| Web UI | `web/` (Next.js) | plate editor, worklist, robot panel; replaces the desktop GUI |
| Python | `requires-python >=3.12` | see section 2 |

So the path from the browser to the robot already exists in outline: edit a plate, plan and check it, generate and simulate a protocol, upload it, start the run, follow its status, take before and after pictures.

## 2. Toolchain facts we verified (Windows, 2026-10-24)

- `opentrons==10.1.0` installs from binary wheels in about 10 to 30 seconds.
- **It does not import on Python 3.11, even with pydantic pinned to the version Opentrons develops against (2.11.7).** Error: "Please use `typing_extensions.TypedDict` instead of `typing.TypedDict` on Python < 3.12". The package metadata still says Python 3.10 or newer, which is wrong in practice. Use **Python 3.12** (`uv venv --python 3.12` fetches it). `ebrinz` already moved the project to 3.12 for this reason.
- Console scripts installed: `opentrons_simulate` and `opentrons_execute`. There is no `opentrons_analyze` script. `python -m opentrons.cli analyze` was not tested (click failed in our non-console shell).
- `opentrons_simulate PROTOCOL` options: `-o {runlog,nothing}`, `-l LEVEL`, `-L` (custom labware dir), `-D`/`-d` (data files), `-e` (duration estimate, experimental, printed 0h:0m for our protocol), `-v`. A 224-transfer protocol simulates in about 6 seconds and prints about 1,100 log lines.
- `capture_image` simulates without error ("Capturing an image."). Whether our Flex has a working camera is not known yet.

## 3. The mismatch: the generator assumes two 1-channel pipettes, our Flex has one 8-channel 1000 µL

`protocol_generator.py` hardcodes a `flex_1channel_50` on the left and a `flex_1channel_1000` on the right, stock tubes in a 24-tube rack, and one tip per transfer. We generated a protocol for a synthetic 7-compound plate (224 transfers, minimum transfer 5 µL) and simulated four versions with `opentrons_simulate` 10.1.0 on Python 3.12:

| Version | Result |
|---|---|
| A. As generated (1-channel 50 and 1-channel 1000) | **Passes**, exit 0 |
| B. Only the pipette names changed to `flex_8channel_1000` | **Fails**: `OutOfTipsError`. An 8-channel `pick_up_tip()` takes a whole column of 8 tips, so the tip racks the generator allocated run out about 8 times faster |
| C. 8-channel with `configure_nozzle_layout(SINGLE, start="H1")` | **Fails**: `PartialTipMovementNotAllowedError`, moving to the deep-well plate in B2 "will result in collision with items" |
| D. 8-channel with SINGLE, `start="A1"` | **Fails**: same error moving to the tip rack in A1, "collision with items in deck slot B1" |

What this means:
- Swapping the pipette is not enough.
- SINGLE-nozzle mode on the 8-channel is fragile on this deck. The generator packs tip racks into adjacent slots (A2, A1, B1) and the 8 nozzles span the neighbouring slots. It can be made to work with a different deck, but expect trial and error in the simulator.
- A 24-tube rack cannot be used in full-column mode (4 rows against 8 nozzles). Stocks need to be in a **plate column** (for example compounds in column 1, rows A to H).

## 4. Recommended 8-channel design: column batches

Use the 8-channel the way it is meant to be used: whole columns.

1. **Layout rule (planner):** compounds in rows A to H, doses across columns, replicates in further columns or plates. We already measured that in an 8-compound layout 10 of 11 dose columns are column-friendly.
2. **Stocks:** a stock plate (96-well, deep-well or PCR) with compound `k` in row `k` of one column. The barcode (G5) identifies this plate.
3. **Generator:** group the planner's per-well transfers into column batches. A batch is a set of 8 transfers with the same phase and volume whose sources are one column A to H of one plate and whose destinations are one column A to H of another. Emit `pick_up_tip()`, `aspirate(volume, source["A<col>"])`, `dispense(volume, dest["A<col>"])`, `drop_tip()` per batch. The medium reservoir is a trough well, which the 8 channels share.
4. **Fallback:** anything that does not batch is reported by the planner as "not 8-channel friendly" and refused, instead of silently using SINGLE mode. Revisit SINGLE mode only if time allows.
5. **Tips:** count tip columns, not tips: a 96-tip rack gives 12 column pickups. Rough estimate for an 8 x 10 plan: about 22 pickups, so 2 racks. Opentrons advises the smallest-capacity tip that fits the volume.
6. **Pipette:** `flex_8channel_1000` on one mount. No `configure_for_volume` (that is for the 50 µL pipettes). Minimum transfer 5 µL (planner default must change from 1 µL).
7. **Gripper:** use `move_labware(..., use_gripper=True)` at least once (for example to present the assay plate to the camera or move it to a clean slot before dosing).
8. **Assay plate:** the planner assumes it is pre-filled with medium. Either keep that (someone fills it by hand before the run) or add a `fill` phase so the robot does it. Decide this before building.

Acceptance: the generated protocol simulates on 10.1.0 for the 7 x 10 example, an independent check of the simulated aspirate and dispense volumes per well matches the plan within 0.01 µL, and the simulator's collision checks pass with the real deck map.

## 5. Robot side: gaps in the client and API

- **Login.** Robot software 10.x adds user accounts, tokens and roles. On our robot reads work without a token (checked, see [robot-check-2026-10-24.md](../robot-check-2026-10-24.md)). Writes (upload, create run, play) were not tried, so keep the optional token support (`FLEX_TOKEN`, bearer header, never in the repo) in case they are refused.
- **No per-command feed.** The spec lists `commands(run_id)` but the client does not implement it. G10 needs it: `GET /runs/{id}/commands` returns each command with its status and timestamps, which can become ledger events.
- **Camera endpoints exist.** The robot's OpenAPI lists `POST /camera/capturePreviewImage` and `POST /camera/picture`. `capturePreviewImage` with body `{"data": {}}` returned a JPEG, and zoom, pan, brightness, contrast and saturation settings are accepted. `capture_image` inside the protocol is a second route.
- **Start gate.** `POST /robot/runs` starts the stored `protocol.py` without checking that it simulated cleanly. Refuse to start unless the last simulation passed for that exact file (compare a hash).
- **No labware offsets.** Runs started over HTTP use nominal positions. Run Labware Position Check in the Opentrons App for the first real run.
- **Wi-Fi.** Reachability from the laptop to the Flex is untested (see G3 in `GOALS.md`). The `flex health` command is the first thing to run on the robot.
- **Hardware constants.** The generator's deck, pipettes and labware are constants. Update them from the real inventory (Q3) and keep one deck map file as the single source.

## 6. Work list

| # | Task | Owner | Done when |
|---|---|---|---|
| 1 | Merge `ebrinz` into `main` (up to date, `uv run pytest` green) | `ebrinz` | `main` has the web UI, API, CLIs, generator, client |
| 2 | Python 3.12 on every laptop (`uv python install 3.12`) and `uv sync` | everyone | `uv run pytest` runs on all three |
| 3 | Planner: 5 µL default, column-friendly check, stock-plate location, fill phase decision, intermediate plate capacity (G1) | `steffiAI` suggested | demo layout plans with no warnings |
| 4 | Generator: 8-channel column batches, stock plate, tip columns, deck map file | unclaimed | 7 x 10 example simulates on 10.1.0 and the volumes check passes |
| 5 | Robot check on the real Flex | done 17:30 PDT | results in [robot-check-2026-10-24.md](../robot-check-2026-10-24.md). Still open: writes need a login?, labware and tip types on the deck |
| 6 | Client: optional token, `commands()`, start gate | unclaimed | mock-transport tests pass |
| 7 | Ledger feed from `commands()` into the Live plates view (G10) | unclaimed | run on the mock robot updates the view |
| 8 | CI: GitHub Action running pytest and a simulation of the example protocol on Python 3.12 | unclaimed | green on `main` |

## 7. Reproduce the tests

```bash
uv venv --python 3.12 .venv-ot && uv pip install --python .venv-ot/Scripts/python.exe opentrons==10.1.0
.venv-ot/Scripts/opentrons_simulate.exe runs/<plate>/protocol.py
```

On Python 3.11 the second command fails on import with the TypedDict error above.

## 8. Coordination notes (Saturday about 18:00 PDT)

- **Two deck layouts.** The generator on `main` assumes single-nozzle mode (tips D1 to D3, row A empty, tube rack B1, assay B2, intermediate B3, medium C2). `medium_fill.py` and the physical deck use full-column mode (tips A1 and A2, reservoir B1, stock plate B2, PCR plate on a riser B3). Pick one layout for dosing and keep it in one deck map.
- **Planner contract change pending on `steffi/plate-designer`.** Her branch (not merged) renames the medium source from `medium` to `reservoir`, adds an `edge` phase and reservoir wells, and repurposes the `MEDIUM` constant as a liquid name. The generator imports `MEDIUM` as a labware key, so it breaks after that merge (its tests should catch it). Her branch is also based on the code from before the web UI and still edits the deleted desktop GUI files, so merging `main` into it will conflict on `main.py` and `ui_helpers.py`.
- **Filter tips.** The rack in A1 is loaded as `opentrons_flex_96_tiprack_1000ul`, but its label in the camera picture looked like a filter rack. Check it.
