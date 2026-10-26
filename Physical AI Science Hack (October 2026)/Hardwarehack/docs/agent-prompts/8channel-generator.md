# Agent task: make the Flex protocol generator work with our 8-channel pipette

**Paste this into your Claude Code session** (Hardwarehack clone, on your own branch):

> Read `docs/agent-prompts/8channel-generator.md` completely, then `docs/opentrons-integration.md` and `CLAUDE.md`. Do the tasks in the order given, commit small, run the verification commands, and finish with the report described in section 8. If anything here conflicts with what ebrinz tells you, follow ebrinz and say so in the report.

If the file is not in your working tree yet (it lives on the planning branch until it is merged), copy it in without touching your branch history:

```bash
git fetch origin lamasu/goals-and-plan
git checkout origin/lamasu/goals-and-plan -- docs/agent-prompts docs/opentrons-integration.md GOALS.md
```

## 0. Rules of engagement

- This brief comes from LamaSu's planning session. Planning and review come from there, the team writes the code. You are the one writing it.
- The repo is public. No secrets, robot IP addresses, serial numbers or proprietary compound data in commits or test fixtures. Keep any robot token in an environment variable.
- `CLAUDE.md` applies: your own branch, never push to `main`, pull `main` into your branch often, `uv run pytest` green before merging, never force-push. Its security section stays true: both servers on loopback only, user text in generated protocols only as a `repr()` literal or through `_comment_text`.
- Deadline: final submission Sunday 2:30 PM PDT. Robot time: tonight until midnight, then Sunday from 8 AM. Code that has not simulated cleanly must not reach the robot.
- Prefer the smallest change that meets each acceptance check. Do not refactor unrelated code.

## 1. Situation

- Robot: Opentrons Flex, robot software 10.1.0, ours alone for the weekend. Checked on the robot (see [docs/robot-check-2026-10-24.md](docs/robot-check-2026-10-24.md)): a plate gripper and **one 8-channel 1000 µL pipette on the LEFT mount**, no second pipette, no modules, a working camera, a trash bin in A3, no staging slots, reads need no login. On the deck: probably 1000 µL filter tips in A1 and 50 µL filter tips in A2, one clear plate in each of B1 to B3 (types unknown), everything else empty. Use the filter-tip load names if the boxes say filter.
- Flex 8-Channel 1000 µL pipette: **5 to 1000 µL**, tips 50, 200 or 1000 µL. The 1 µL minimum in the planner belongs to the 50 µL pipettes. Our minimum transfer is **5 µL**.
- Protocol API goes up to 2.30. Instrument load name: `flex_8channel_1000`.
- `opentrons==10.1.0` only imports on Python 3.12 or newer (3.11 fails with a pydantic TypedDict error). The project already requires 3.12.
- Track B of the event: "Build and test new liquid-handling workflows on the Flex."
- What exists on your branch: `src/protocol_generator.py` (self-contained protocol, transfers embedded, `capture_image` before and after), `src/flex_client.py` (+ `MockFlexClient`), `src/simulation.py`, `src/run_store.py`, `src/planning.py`, `cli/plate.py`, `cli/flex.py`, `api/`, `web/`.
- The generator currently hardcodes `flex_1channel_50` (left) and `flex_1channel_1000` (right), stocks in a 24-tube rack, one tip per transfer.

## 2. Evidence (Opentrons 10.1.0 simulator, Python 3.12.12, 7-compound synthetic plate, 224 transfers, minimum 5 µL)

| Version | Result |
|---|---|
| As generated today (1-channel 50 and 1000) | passes, exit 0 |
| Only the pipette names changed to `flex_8channel_1000` | `OutOfTipsError`: an 8-channel `pick_up_tip()` takes a column of 8 tips |
| 8-channel + `configure_nozzle_layout(SINGLE, start="H1")` | `PartialTipMovementNotAllowedError`: moving to the deep-well plate in B2 "will result in collision with items" |
| 8-channel + SINGLE, `start="A1"` | same error moving to the tip rack in A1, "collision with items in deck slot B1" |
| 8-channel in **full-column mode** (below) | passes, exit 0, including `capture_image` and gripper `move_labware` |

So: do not use SINGLE-nozzle mode. Use whole columns. This pattern is verified to simulate:

```python
pipette = protocol.load_instrument("flex_8channel_1000", "left", tip_racks=[tips])
pipette.pick_up_tip()                      # takes a column of 8 tips
pipette.aspirate(95, medium["A1"])         # trough well: 8 tips share it
pipette.dispense(95, intermediate["A1"])   # "A1" addresses the whole column A to H
pipette.drop_tip()
pipette.pick_up_tip()
pipette.aspirate(5, stock["A1"])           # stock plate column 1, compound k in row k
pipette.dispense(5, intermediate["A1"])
pipette.mix(3, 50, intermediate["A1"])
pipette.drop_tip()
protocol.move_labware(assay, "D3", use_gripper=True)   # gripper move simulates too
```

Deck used in that run: trash bin A3, tips B3 and A2 (`opentrons_flex_96_tiprack_1000ul`), stock plate C1 (`nest_96_wellplate_2ml_deep`), intermediate B2 (`nest_96_wellplate_2ml_deep`), assay C2 (`corning_96_wellplate_360ul_flat`), medium D2 (`nest_12_reservoir_15ml`). Each log line "Picking up tip from A2" means the second tip column.

## 3. Tasks, in priority order

### P0. Generator: 8-channel column batches (the main task)

1. Pipette constants at the top of the generated protocol: `("flex_8channel_1000", "left")`, tip rack load name, flow rates, mix policy, `USE_GRIPPER`, `USE_CAMERA`. One deck map (a small module or dict) is the single source of truth for the generator, the materials list and the API response. No `flex_1channel_*`, no `configure_for_volume`, no `configure_nozzle_layout`.
2. Labware roles: `stock` becomes a **96-well plate** (default `nest_96_wellplate_2ml_deep`, configurable), `intermediate` stays `nest_96_wellplate_2ml_deep`, `assay` is the layout's labware, `medium` is `nest_12_reservoir_15ml` (or the 195 mL one) with the 8 tips in well `A1`. Stock tubes and the 24-tube rack go away.
3. Stock mapping: compound `k` sits in the stock plate row that matches the intermediate-plate row of its first intermediate, in column 1. Print this map as a comment block at the top (like the tube map today) and return it from the API so the person loading the plate sees it.
4. **Batching.** The planner emits per-well transfers. Group them into column batches. A batch is 8 transfers that have the same `phase`, `source_labware`, `dest_labware`, a volume equal after rounding to 0.001 µL, sources that are rows A to H of one column (or the single medium trough well) and destinations that are rows A to H of one column, in the same row order. Emit `pick_up_tip`, `aspirate(v, source["A<col>"])`, `dispense(v, dest["A<col>"])`, optional mix, `drop_tip` per batch.
5. **Order.** Never reorder across dependencies. Give each transfer a level (0 if its source is not written by an earlier transfer, otherwise 1 + the highest level of the transfers that write its source well) and batch only inside the same level, phase and volume. Keep the planner's original order otherwise.
6. **Refuse what cannot batch.** If a transfer cannot be part of a full batch (fewer than 8 rows in a column, different volumes across rows, a source that is one intermediate well feeding several destination rows) raise `ProtocolError` naming the wells and the reason. Do not fall back to SINGLE mode silently.
7. **Tips.** One tip column per batch. A 96-tip rack gives 12 batches. Allocate racks from the batch count and raise `ProtocolError` when the deck has no room. Rough estimate for an 8 x 10 plan: about 22 batches, so 2 racks.
8. **Volumes.** Each aspirate must be between 5 µL and the tip capacity. Split above the tip capacity as today. Set `pipette.flow_rate.aspirate/dispense` from constants (the default is 716 µL/s, too fast for 5 to 10 µL and for DMSO, tune on the robot).
9. **Camera and gripper.** Put the `capture_image` calls behind `USE_CAMERA` (default on) so a robot without a camera can still run. Add one gripper `move_labware` of the assay plate behind `USE_GRIPPER` (default off until someone has run it on the robot).
10. **Assay pre-fill.** Keep the planner's assumption (a person fills the assay plate) as the default. Add `prefill_assay: bool = False`; when true, add a `fill` phase that dispenses medium into the assay columns first. Do not change the default without asking.

### P1. Planner: 8-channel mode (coordinate with `steffiAI`, make the smallest change in their modules and tell them)

1. `PipettingSettings.min_transfer_ul` default 5.0, everywhere it is shown or defaulted (code, CLI help, API schema, web form, README).
2. Make `check_plan` fail when any intermediate has no well. Today it prints "Intermediate plate is full" in `plan.warnings` but the checker still passes at 1 µL. We measured: 8 compounds x 10 doses plus a vehicle control overflows the 96-well plate (2 intermediates get no well at 5 µL); 7 x 10 and 6 x 12 fit.
3. Column-friendly check: a function that says whether a layout and plan can run in column mode (8 rows used, uniform volumes per column) and lists the reasons if not. The API `/plan` response and the CLI print it; the web UI shows it.
4. Vehicle control: its single intermediate cannot feed 8 destination rows from one well. Replicate it down one free column of the intermediate plate (8 wells, one per row) so the vehicle dose is a column batch too. Column 12 is free in every compound row when there are 10 doses.
5. Layouts for the demo are 8 rows of dose series (8 compounds or dyes) with identical stock concentration and dose scheme, untreated wells in a spare column. Assume normalised stocks. Say so in the error message when stocks differ across rows.

### P2. Robot client and API safety

1. Optional login token: `FLEX_TOKEN` (env only) sent as a bearer header when set, never logged, never in the run store. Test with `httpx.MockTransport` that the header is present only when set.
2. Start gate: `POST /robot/runs` and `flex run` refuse to start unless the stored `protocol.py` has a recorded successful simulation of the exact same bytes (hash). `--force` overrides on the CLI only.
3. `flex health` also prints whether `GET /protocols` is allowed without a login (200 vs 401 or 403) so we learn on the robot whether 10.x requires one.

### P3. Per-command feed (for the live well view, G10 in `GOALS.md`)

1. `FlexClient.commands(run_id)`: `GET /runs/{id}/commands` with paging, returns a list of normalised events: command type, status, created/started/completed timestamps, and for `aspirate` and `dispense` the labware, well and volume. `MockFlexClient.commands()` returns a plausible list.
2. API route `GET /robot/runs/{id}/commands` for the web UI. No UI work needed yet.

### P4. Only if time remains

Tip size per volume (50 µL tips for small volumes), liquid presence detection, labware offsets over HTTP, `flex demo` using the new pieces end to end.

## 4. How to verify

```bash
cd drug-screen-platform
uv python install 3.12        # once
uv sync
uv run pytest
uv run plate check            # example plate
uv run plate protocol <layout.json>
uv run plate simulate runs/<plate>/protocol.py
```

Add tests to `tests/test_protocol_generator.py` that run the **real simulator** (no mocks) for:
- an 8-compound x 10-dose layout at 5 µL: simulation passes, the source contains `flex_8channel_1000` and none of `flex_1channel`, `configure_nozzle_layout`, `configure_for_volume`;
- a volume audit: parse the simulator run log lines "Aspirating V uL from A<col> of ..." and "Dispensing V uL into A<col> of ..." (one line per column batch, each applies to rows A to H of that column; ignore the tab-indented mix lines), rebuild the per-well volumes and compare with `check_plan`'s simulated wells within 0.01 µL;
- a 7-row layout and a layout with different volumes across rows each raise `ProtocolError` with the wells in the message;
- the number of tip pickups equals the number of batches and fits the racks.

Keep `tests/test_plan_checker.py` green (300 random layouts).

## 5. Acceptance checklist

- [ ] `uv run pytest` passes on Python 3.12
- [ ] 8 x 10 example generates and simulates on opentrons 10.1.0, volume audit passes
- [ ] Generated source has no 1-channel pipette, no nozzle-layout call, `USE_CAMERA` and `USE_GRIPPER` switches
- [ ] `ProtocolError` messages name the wells that block batching
- [ ] `min_transfer_ul` default is 5 everywhere; `check_plan` fails on an intermediate with no well
- [ ] Start gate, token support and `commands()` have tests with `httpx.MockTransport`
- [ ] No secrets, IPs or serial numbers in the diff; loopback-only security tests still pass

## 6. Out of scope

SINGLE or PARTIAL_COLUMN nozzle modes, 384-well plates, image analysis, LIMS, the live well view itself, changes to `web/` beyond showing the new messages.

## 7. Open questions (ask ebrinz or LamaSu, do not guess)

- Real deck contents: the exact tip racks (filter or not, sizes), which plate holds the stocks, the medium reservoir type. The robot check shows no second pipette and no modules.
- Do writes (upload, create run, play) need a login? Reads do not.
- Assay pre-fill by hand or by the robot?
- How many compounds and doses will the demo use?

## 8. Report format

End with: files changed, the commands you ran with their real output (pass or fail), what you did not verify, and the open questions you hit. "Written, not tested" is an acceptable status for anything you could not run. Do not weaken or skip a test to make it pass.

## Reference

- Partial tip pickup rules and warnings: https://docs.opentrons.com/v2/pipettes/partial_tip_pickup.html
- Pipette load names: https://docs.opentrons.com/v2/pipettes/loading.html
- Pipette volume ranges: https://docs.opentrons.com/flex/system-description/pipettes/
- API versions: https://docs.opentrons.com/v2/versioning.html
- Evidence and context: `docs/opentrons-integration.md`; goals and plan: `GOALS.md`
