# Hardwarehack: goals and plan

**Physical AI for Science Hack @ Studio 45, Track B (Opentrons).** Draft for team review, written Saturday 2026-10-24 about 16:00 PDT and updated about 16:05 PDT after the planner landed on `main`, again about 16:15 PDT to add G10, and again about 16:45 PDT after `ebrinz`'s web UI, API and Flex tooling (details in [docs/opentrons-integration.md](docs/opentrons-integration.md)). Questions and answers live in [issue #1](https://github.com/LamaSu/Hardwarehack/issues/1). This repo is public: no keys, IP addresses, robot serial numbers or proprietary compound data in it.

## Vision

Scan a sample plate, say which concentration you want in which wells, press go. The Flex does the dilutions and a sample log remembers every transfer from stock to intermediate to assay well.

The demo in five steps:

1. Scan the stock plate's barcode. The app loads each stock's compound, concentration, solvent and volume.
2. Choose target concentrations and wells in the Drug Screen Designer (GUI) or with the CLI.
3. The planner computes volumes and intermediate dilutions. The plan checker replays the plan and confirms every well.
4. A Flex protocol is generated, simulated, then run on the Flex (8-channel 1000 µL pipette, plate gripper).
5. A live plate view shows every well (volume, liquids, concentrations, timestamps and the actions taken on it) as the run proceeds, and the stock inventory goes down as it is used.

Track B brief on the event page: "Build and test new liquid-handling workflows on the Flex." Prizes, judging criteria and demo length are not stated on either Luma page. Ask a host.

## Facts we build on

| Topic | Fact | Source |
|---|---|---|
| Schedule | Sat 10/24 9:30 AM to Sun 10/25 5:30 PM PDT. Hacking from Sat 12 PM, robots sleep at Sat midnight, doors open Sun 8 AM, **final submission Sun 2:30 PM**, demos from 3:30 PM. Everyone demos something. The two pages list slightly different Sunday agendas. | [hack page](https://luma.com/3vc5oeit), [demos page](https://luma.com/t73di5w3) |
| Robot | Opentrons Flex, robot software 10.1.0 (released 2026-10-15), ours for the whole weekend, plate gripper and 8-channel 1000 µL pipette, connected over Wi-Fi. | team, [release](https://github.com/Opentrons/opentrons/releases/tag/v10.1.0) |
| Pipette | Flex 8-Channel 1000 µL: **5 to 1000 µL**. Tips 50, 200 or 1000 µL. The 1 µL minimum belongs to the 50 µL pipettes. | [Opentrons docs](https://docs.opentrons.com/flex/system-description/pipettes/) |
| Python | `opentrons==10.1.0` is on PyPI. Its metadata says Python 3.10 or newer, but the simulator only imports on **Python 3.12 or newer** (tested on 3.11: fails). Protocol API goes up to 2.30. Load name `flex_8channel_1000`. | PyPI, [versioning](https://docs.opentrons.com/v2/versioning.html), [loading pipettes](https://docs.opentrons.com/v2/pipettes/loading.html) |
| 8-channel layouts | Full column (default), SINGLE (start A1 or H1) and PARTIAL_COLUMN (start H1, 2 to 7 tips). The last two need API 2.20. Pass `tip_racks` on every `configure_nozzle_layout()` call. | [partial tip pickup](https://docs.opentrons.com/v2/pipettes/partial_tip_pickup.html) |
| CSV parameter | `parameters.add_csv_file(...)` from API 2.20. One CSV per run, picked at run setup in the Opentrons App or from a USB drive on the touchscreen. | [parameters](https://docs.opentrons.com/v2/parameters/defining.html) |
| Gripper | `move_labware(..., use_gripper=True)` since API 2.15. | versioning page |
| Robot login | 10.x adds user accounts, login tokens, roles and audit logs. Reads on our robot work without a token; writes are untested. | release notes v10.0.0 and v10.1.0 |
| Planner | Drug Screen Designer, now on `main` in `drug-screen-platform/` (merged 15:46 PDT): plate layouts, dose series, C1·V1=C2·V2, automatic intermediate dilutions, an ordered transfer list (CSV) and an independent plan checker. On `main`: Python 3.11, uv, CustomTkinter desktop app. On branch `ebrinz` (not merged yet): Python 3.12, FastAPI backend, Next.js web UI, `plate` and `flex` CLIs, a Flex protocol generator and a robot client. | this repo |

## Scope

**MVP (must work by the Sunday 12:30 PM feature freeze)**
- Plan, check, generate a protocol, simulate it, and run a real dye dose-response plate on the Flex with the 8-channel pipette and the gripper.
- A barcode step before the run that loads the stocks (real scanner or mock).
- A well ledger (SQLite) behind a live plate view: every well's contents, timestamps and actions, with provenance from stock to intermediate to assay well and the stock volume remaining (G10).
- A CLI for the non-browser steps, plus the web UI for layout design.
- README, a 2-minute and a 5-minute demo script, a backup video.

**Stretch**
- A real LIMS behind the sample-log adapter.
- Starting and monitoring runs from the CLI through the robot's HTTP API (may need a login token).
- Label printing, camera scanning, liquid-level detection, PubChem molecular weights, 384-well plates.

**Out of scope**
- Real patient data, proprietary compounds, hazardous materials, cell culture. Dye and water stand in for drugs unless the team decides otherwise (Q6).

## Workstreams

Nobody is assigned yet. Claim one by commenting on issue #1 or by editing this table in a PR. "Suggested" is a proposal, not an assignment.

| # | Workstream | Suggested owner | Needed by (PDT) |
|---|---|---|---|
| G1 | Planner ready for the 8-channel | `steffiAI` (planner author) | Sat 6 PM |
| G2 | Transfer list to Flex protocol | unclaimed | Sat 9 PM (first simulation) |
| G3 | Robot bring-up and runs | whoever is at the robot | Sat 6 PM (hello world), Sat 11 PM (first dye run) |
| G4 | CLI | unclaimed | Sun 11 AM |
| G5 | Barcodes | unclaimed | Sat 11 PM (mock), Sun 11 AM (real) |
| G6 | Sample log and LIMS | unclaimed | Sun 8 AM |
| G7 | Verification | everyone | continuous |
| G8 | Demo and submission | unclaimed | Sun 2:00 PM |
| G9 | Repo and team hygiene | everyone | now |
| G10 | Live well ledger and inventory | unclaimed (suggest `steffiAI` for the ledger and view) | Sat 11 PM (simulated), Sun 11 AM (robot feed, stretch) |

### G1. Planner ready for the 8-channel
Goal: plans the 8-channel 1000 µL pipette can actually execute.

- Done: the planner is on `main` (merged 15:46 PDT).
- Make the default minimum transfer 5 µL instead of 1 µL (code, GUI, README, `verify_plan.py`). The 1 µL figure belongs to the 50 µL pipettes.
- Fix the intermediate plate capacity. We ran the planner's modules on a synthetic layout (96-well assay plate, 100 µL wells, 10 mM DMSO stocks, 3-fold series from 10 µM, vehicle and untreated controls):

  | Layout | min 1 µL | min 5 µL |
  |---|---|---|
  | 8 compounds x 10 doses | 81 intermediates, 1 has no well | 90 intermediates, 2 have no well, checker fails |
  | 8 compounds x 12 doses, no controls | 96, fits | 104, 52 have no well, checker fails |
  | 7 compounds x 10 doses | 71, fits | 79, fits, checker passes |
  | 6 compounds x 12 doses | 61, fits | 68, fits, checker passes |

  Every compound starts on a new row of the 96-well intermediate plate, so 8 compounds leave no row for the vehicle control. The planner prints "Intermediate plate is full", but the checker still passes at 1 µL. Fix: a second intermediate plate or tighter packing, and make the checker fail when any intermediate has no well. Until then, size demo layouts to fit, for example 7 compounds x 10 doses.
- Make the plan carry what the protocol needs and the CSV lacks: the medium pre-fill volume per assay well (or an explicit `fill` phase), a physical stock location per compound (today `source_well` holds the compound name), and the medium reservoir well (today the literal `reservoir`).
- Fix the docs: they say "Track 3 (open track)", we are Track B (Opentrons).

Good news: in the 8-compound layout, 10 of 11 dose columns are already column-friendly (8 rows, one volume, intermediates in one column with matching rows), so the 8-channel can dose a whole column per move.

Done when: the demo layout plans at 5 µL with no warnings, every transfer is at least 5 µL, `check_plan` passes and `uv run pytest` is green.

### G2. Transfer list to Flex protocol
Goal: turn the ordered transfer list into a Flex Python protocol that simulates cleanly.

Status (16:45 PDT): a first generator exists on branch `ebrinz` (`src/protocol_generator.py`). It embeds the transfers and assumes two 1-channel pipettes. It simulates cleanly as written, but fails with the 8-channel (out of tips, then collision errors in SINGLE-nozzle mode). The 8-channel column-batch rewrite is the work: see [docs/opentrons-integration.md](docs/opentrons-integration.md). A ready-to-paste prompt for the coding agent is in [docs/agent-prompts/8channel-generator.md](docs/agent-prompts/8channel-generator.md).

First decision (30 minutes): (a) one fixed, tested protocol that reads the transfer list as a CSV runtime parameter (API 2.20 or newer), or (b) a generator that writes a self-contained protocol with the transfers embedded. Decided in practice: (b), as built on `ebrinz`'s branch. (a) stays an option if embedding gets awkward.

The protocol must handle:
- A deck map (example below): stock plate, intermediate plate, assay plate, medium reservoir, tip racks and a trash bin (the docs' examples load it at A3).
- The 8-channel: whole-column moves where transfers form a column, SINGLE-nozzle layout for the rest.
- Tips: new tips per source liquid. Opentrons advises the smallest-capacity tip that meets the need. Rough estimate for the demo plan: about 22 column pickups, so plan for 2 tip racks.
- Mixing after adding stock and after dosing, and flow rates suited to DMSO.
- Filling the assay plate with medium first (the planner assumes it is pre-filled).
- At least one plate move with the gripper.

Done when: the simulator that ships with `opentrons==10.1.0` runs the demo plan with no errors, an independent check of the simulated aspirate and dispense volumes per well matches the plan within 0.01 µL, and one `apiLevel` (2.30 or lower) is pinned.

Example deck map (**example only, the real deck is unknown, see Q3**):

```json
{
  "robot": "Flex",
  "pipette": {"load_name": "flex_8channel_1000", "mount": "left"},
  "tip_racks": [{"load_name": "opentrons_flex_96_tiprack_1000ul", "slot": "C2"}],
  "labware": {
    "stock": {"load_name": "nest_96_wellplate_100ul_pcr_full_skirt", "slot": "D1"},
    "intermediate": {"load_name": "nest_96_wellplate_2ml_deep", "slot": "D2"},
    "assay": {"load_name": "corning_96_wellplate_360ul_flat", "slot": "D3"},
    "medium": {"load_name": "nest_12_reservoir_15ml", "slot": "C1"}
  },
  "trash": {"slot": "A3"},
  "gripper": true
}
```

Every load name above exists in the Opentrons labware library.

### G3. Robot bring-up and runs
- Status: `flex health`, `flex run` and `flex demo` exist on branch `ebrinz` (with `--mock`), untested on the real robot. Add token support if the robot requires a login.
- Done (17:30 PDT): the robot is reachable over Wi-Fi from LamaSu's laptop, reads need no login, the camera works. See [docs/robot-check-2026-10-24.md](docs/robot-check-2026-10-24.md).
- Reachability over Wi-Fi: read the Flex's IP off the touchscreen, then `curl -s -H "Opentrons-Version: *" http://<FLEX_IP>:31950/health` (expect `api_version` 10.1.0) and the same for `/protocols` (200 means open, 401 or 403 means a login is required). Do not paste the IP or serial number into this repo.
- If the venue network blocks it: phone hotspot or travel router, an Ethernet cable, USB-B to the laptop with the Opentrons App, or a USB stick into the touchscreen.
- Labware position check, gripper test, tip pickup with the 8-channel, then a water dry run, then a dye run.
- Upload through the Opentrons App first. CLI-driven runs over the HTTP API are a stretch.

Done when: one full run of the demo plan completes on the Flex, with a photo of the plate and a video saved, and the deck layout is written down in `docs/` (no IPs or serial numbers).

### G4. CLI
Status: `plate` (check, plan, protocol, simulate) and `flex` (health, snapshot, run, status, pause, stop, demo) exist on branch `ebrinz`. Still to add: `scan` and `log` (G5, G10). The CLIs call the same `src/` code as the API.

Done when: `--help` lists them, each works on the demo layout JSON, and the demo uses the CLI.

### G5. Barcodes
- A scanner interface with three backends: USB handheld (acts like a keyboard, so read a line from stdin or a focused GUI field), camera (decode in software) and mock (typed or simulated).
- Scanning verifies identity before the run: stock plate against the plan, assay and intermediate plates against the deck map.
- Label generation (Code 128 or QR) so the demo is self-contained.

Done when: scanning a stock plate loads its stocks into the plan, scanning the wrong plate blocks the run with a clear message, and the mock backend runs the whole demo without hardware.

### G6. Sample log and LIMS
- Start with an in-repo registry (SQLite) behind one adapter: `register_container`, `register_content`, `get_by_barcode`, `list_wells`, `record_scan`, `record_transfer`, `adjust_volume`, `get_lineage`, `get_history`, `events_since`, `capabilities`. The registry is also the well ledger of G10. Build brief for a coding agent: [docs/agent-prompts/sample-registry.md](docs/agent-prompts/sample-registry.md).
- Research a real LIMS with barcode scanning and a Python-friendly API, open source and SaaS, and choose by time to first API call. Shortlist to evaluate (not yet checked): eLabFTW, Benchling, LabKey Sample Manager, SENAITE, OpenSpecimen, Quartzy, SciNote, Snipe-IT. Adopt one only if its adapter works before the Sunday 8 AM robot window. Otherwise ship the registry and document the swap.

Done when: after a run, the log shows for each assay well where it came from (stock barcode and well, intermediate well, assay well, volumes, time) and the stock volume has been reduced.

### G7. Verification
- `uv run pytest`, including the plan checker's 300 random layouts, at a 5 µL minimum.
- A golden test for the demo layout.
- A simulation test in CI (GitHub Actions) once G2 lands. There is no CI yet.
- A wet check: a photo of the dye gradient, and plate-reader absorbance if one is available.

Done when: CI is green on `main` and the dye gradient from the demo run is monotonic across doses.

### G8. Demo and submission
- 2-minute and 5-minute scripts, a backup video, a README with an architecture diagram and run instructions, an MIT license at the repo root, and a "Credits and AI assistance" section (the planner reuses code from an earlier calculator project, and commits carry Claude co-author lines). The event pages state no rule on either.
- Submit before the Sunday 2:30 PM deadline, aiming for 2:00 PM. Check whether each of us must register for the final demos.

Done when: someone who did not build it can run the demo from the README in 10 minutes.

### G9. Repo and team hygiene
- Follow the branching rules in `CLAUDE.md`: nobody pushes to `main` directly, each person works on their own branch (`ebrinz`, `steffi/<topic>`, `lamasu/<topic>`), and merges into `main` only when up to date and `uv run pytest` is green. PRs are optional, for when you want a second pair of eyes. Conventional commit messages.
- Add a root `.gitignore` (`.env*`, local config, `data/`). Nothing secret, no IPs, no serial numbers, no proprietary data.
- Resolve the unknowns with a host: demo length, judging criteria, which Sunday agenda is current.

### G10. Live well ledger and inventory
Goal: the GUI shows what is in every well right now, when it got there and what was done to it, and the stock inventory goes down as liquid is used. Scanning a plate loads it.

Design (small and testable):
- **Ledger.** An append-only event log (SQLite in WAL mode, so the CLI and the GUI can share it). One event per action per well. Fields: `id`, `ts` (UTC, ISO 8601), `run_id`, `source` (`sim`, `robot`, `scan`, `manual`), `action` (`scan_plate`, `register_stock`, `fill`, `aspirate`, `dispense`, `mix`, `move_plate`, `discard`, `note`), `labware` (role and barcode), `well`, `liquid`, `volume_ul` (positive added, negative removed), `step` (the transfer step number), `channel`, `detail`.
- **State.** A reducer replays the events into per-well contents: total volume, each compound's amount (so its concentration), solvent volumes, medium volume, and the event history. The math already exists as `_WellContents` in `plan_checker.py` (well-mixed assumption). Move it into `src/well_ledger.py` so the offline checker and the live view cannot disagree.
- **Inventory.** Stock wells are ledger wells too. Aspirating from a stock reduces its remaining volume, and the same call goes through the sample-log adapter (G6), so SQLite today and a LIMS later show the same number. Warn when a stock would drop below its dead volume.
- **Scan.** `scan_plate(barcode)` looks the plate up (G5, G6), loads its stocks into the ledger and the plan, and logs a `scan_plate` event. Unknown barcode: block with a clear message, or register it in the mock flow.
- **Three ways to feed it.** (1) Simulation: a runner plays `plan.transfers` with timestamps. This is the digital twin and works without the robot. (2) Robot, live: poll the run's commands over the robot's HTTP API (each `aspirate` and `dispense` carries a well, a volume and start and finish times). It may need a login, so it is a stretch. (3) Robot, after the fact: import the run log and compare it with the simulation, flagging any difference.
- **Multi-channel.** An 8-channel move writes eight events that share a `step` and carry a `channel` number.
- **GUI.** A "Live plates" tab in the web UI (`web/`) showing the stock, intermediate and assay plates. Each well is coloured by liquid and filled by volume. Click a well to see its contents (liquids, volumes, concentrations, solvent %) and its history (time, action, volume, step). A strip shows the stock inventory. The tab polls the API every half second, and the ledger logic lives in `src/`.

Build order (each step is demoable):
1. Ledger core, reducer and tests: replaying a plan's transfers gives the same final wells as `check_plan` for the 300 random layouts.
2. Simulation runner and the Live plates tab.
3. Scan hook with the mock scanner: a scan loads the stocks, and stock volumes drop during the run.
4. Robot feed (stretch).

Done when: in simulation, scanning the stock plate barcode fills the stock view, running the plan fills the wells one action at a time, clicking any well shows its liquids, concentrations, timestamps and actions, the stock inventory has dropped by the volumes used, and the final ledger agrees with `check_plan`.

## Hand-offs between workstreams

| Hand-off | Status | Notes |
|---|---|---|
| Layout JSON (`PlateLayout.to_dict`) | exists | wells, stocks, pipetting settings |
| Transfer list CSV | exists | columns: step, phase, source_labware, source_well, dest_labware, dest_well, volume_ul, liquid. Labware are roles (stock, medium, intermediate, assay), not deck slots. |
| Plan extras | new (G1) | medium pre-fill per assay well, physical stock location per compound, reservoir well |
| Deck map | new (G2, G3) | role to labware load name and slot, tip racks, trash, gripper |
| Ledger events and run record | new (G10, G6) | event schema in G10, plus run id, protocol file hash and scanned barcodes |

## Schedule (PDT)

| When | Target |
|---|---|
| Sat now to 6 PM | Merge `ebrinz` into `main` and get everyone on Python 3.12; fix the 5 µL default, decide the G2 design, robot hello world (connect, labware position check, tip pickup, gripper moves a plate), choose the barcode and LIMS routes |
| Sat 6 to 7 PM | Dinner. 10-minute sync: what is merged, what is blocked |
| Sat 7 PM to midnight | First real dye run, scan and log in the loop. At least one end-to-end pass before the robots sleep |
| Sun 8 to 11 AM | Full run, record the backup video, fix what broke |
| Sun 11 AM to 12:30 PM | Feature freeze at 12:30, README and demo script |
| Sun 12:30 to 2:00 PM | Rehearse, final run if needed, submit by 2:00 PM (deadline 2:30 PM) |
| Sun 3:30 PM | Demos begin |

About 9 hours of robot time remain on Saturday evening and 6.5 on Sunday morning, so everything must simulate cleanly before it touches the robot.

## Risks

| Risk | Mitigation |
|---|---|
| 5 µL is the bottom of the pipette's range, so small transfers are less accurate | Design transfers of 10 to 20 µL or more where possible, use a smaller tip for small volumes, check the dye gradient |
| The planner thinks per well, the 8-channel works in columns | Keep drugs in rows and doses in columns so dosing batches by column, fall back to SINGLE-nozzle moves |
| Intermediate plate overflow at 5 µL | G1 fix, and size demo layouts to fit until then |
| Venue Wi-Fi may block the laptop from reaching the Flex, and 10.x may require a login | Test reachability now (G3), keep the Opentrons App and USB routes as the default |
| Little robot time | Simulate first, dry-run with water, record a backup video |
| Judging criteria and demo length unknown | Ask a host, prepare 2-minute and 5-minute versions |
| Large single `main.py` GUI file collides when several people edit it | Keep GUI hooks small, put logic in `src/`, merge often |
| No CI, tests only run when someone remembers | Add a GitHub Action for pytest, add simulation once G2 lands |
| LIMS integration eats the weekend | In-repo registry first, real LIMS only as a stretch behind the same adapter |
| The live robot feed needs network access or a login | Simulation and the after-run import are the default, live polling is a stretch |
| `opentrons` 10.1.0 only imports on Python 3.12 or newer | Everyone runs `uv python install 3.12`, CI uses 3.12 |
| The generator assumes 1-channel pipettes, our Flex has the 8-channel | Column batches plus a stock plate, see [docs/opentrons-integration.md](docs/opentrons-integration.md) |

## Questions from issue #1

| Q | Topic | Status |
|---|---|---|
| Q1 | Timing and rules | Schedule known. Prizes, judging criteria, demo length and any rule on pre-existing code or AI use are not stated on the Luma pages. |
| Q2 | Robot | Answered: Flex, exclusive use. |
| Q3 | Deck | Checked on the robot ([docs/robot-check-2026-10-24.md](docs/robot-check-2026-10-24.md)): 8-channel 1000 µL on the left mount, gripper, no second pipette, no modules, trash bin in A3, no staging slots. Camera pictures show tip racks in A1 and A2, clear plates in B1 to B3, everything else empty. Exact labware and tip types still need a person to confirm. |
| Q4 | Control path | Default: Opentrons App first, CLI-driven runs as a stretch. |
| Q5 | Connectivity | Wi-Fi. The robot is reachable from LamaSu's laptop and reads need no login (writes untested). `opentrons==10.1.0` installs fine but only imports on Python 3.12 or newer. |
| Q6 | Samples | Unanswered. Default: dye stand-ins. |
| Q7 | Source and destination | Unanswered. Suggested: stock plate with compounds in column 1 rows A to H, 2 mL deep-well intermediate plate, 96-well flat assay plate. |
| Q8 | Targets and wells | Answered by the planner: select wells in the GUI, dose series, per-well targets. |
| Q9 | Guardrails | Minimum 5 µL for this pipette (G1), DMSO flag at 0.5% exists. |
| Q10 | Scanner | Unanswered. Default: USB handheld, mock if none. |
| Q11 | LIMS access | Decided 17:56: in-repo SQLite registry behind an adapter first. Research found no adoptable LIMS in 24 hours. An optional 45-minute InvenTree test comes only after the registry works. Brief: [docs/agent-prompts/sample-registry.md](docs/agent-prompts/sample-registry.md). |
| Q12 | What to track | Proposal in G6. |
| Q13 | Stack | Answered by `ebrinz`'s branch: Python 3.12, FastAPI, Next.js, Typer CLIs (replaces the desktop GUI once merged). |
| Q14 | Demo machine | Unanswered. |
| Q15 | Owners | Unanswered: claim a workstream above. |
| Q16 | Repo rules | Answered by `ebrinz`'s branching rules in `CLAUDE.md` (15:46 PDT). Still open: an MIT license at the repo root, a root `.gitignore`, nothing secret in the repo. `ebrinz` also replied "looks good to me" on the issue, read here as agreeing with the defaults. |

## Working agreement

- Done means watched-it-work: say what you ran and what you saw. "Written, not tested" is a fine status.
- Keep everything the robot needs in `src/`, not in `api/`, `cli/` or `web/`.
- The branching rules are in `CLAUDE.md`. Pull `main` into your branch often.
- Planning and review support comes from Claude Code in LamaSu's session. Code changes come from the team.

Drafted with Claude Code at LamaSu's request. Edit freely.
