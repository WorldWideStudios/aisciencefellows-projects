# Agent task: build the sample registry and well ledger

**Paste this into your Claude Code session** (Hardwarehack clone, on your own new branch, for example `lamasu/registry` cut from `main`):

> Read `docs/agent-prompts/sample-registry.md` completely, then `GOALS.md` (G5, G6, G10), `docs/opentrons-integration.md` and `CLAUDE.md`. Do the tasks in the order given, commit small, run the verification commands, and finish with the report described in section 8.

If the file is not in your working tree yet (it lives on the planning branch until it is merged), copy it in without touching your branch history:

```bash
git fetch origin lamasu/goals-and-plan
git checkout origin/lamasu/goals-and-plan -- docs/agent-prompts docs/opentrons-integration.md docs/robot-check-2026-10-24.md GOALS.md
```

## 0. Rules of engagement

- This brief comes from LamaSu's planning session. Planning and review come from there, the team writes the code. You are the one writing it.
- The repo is public. No secrets, robot IP addresses or serial numbers, no proprietary compound data. Demo data is dye stand-ins.
- `CLAUDE.md` applies: your own branch, never push to `main`, pull `main` into your branch often, `uv run pytest` green before merging, never force-push. Both servers stay on loopback only. Keep logic in `src/`, not in `api/`, `cli/` or `web/`.
- Python 3.12 with uv. Standard library plus what is named below. No external database server, no external LIMS.
- Deadline: final submission Sunday 2:30 PM PDT. The registry core should be done and tested by about 11 PM tonight so the robot runs tomorrow can use it.
- Do not edit `src/protocol_generator.py`, `src/dilution_planner.py` or `web/`. They are other people's files and are moving. Everything you need is read-only for you.

## 1. What and why

The demo story is: scan a plate barcode, the app knows what is in it, the robot runs, and every well's contents, timestamps and actions are recorded and shown live while the stock inventory goes down. Research found no existing LIMS we can adopt in 24 hours, so we build a small in-repo registry behind an adapter interface. A real LIMS (InvenTree is the only candidate worth a short test) can be swapped in later.

The registry is also the **well ledger** (G10): an append-only event log plus the current contents of every well, so the Live plates view in the web UI can poll it.

## 2. Data model (SQLite, one file)

File: `drug-screen-platform/runs/registry.sqlite3` (the `runs/` folder is git-ignored; use `run_store.RUNS_DIR`). Open with `PRAGMA journal_mode=WAL`, `foreign_keys=ON`, a busy timeout, so the CLI, the API and a test can share it.

| Table | Fields |
|---|---|
| `containers` | id, barcode (unique, printable ASCII), kind (`stock_plate`, `intermediate_plate`, `assay_plate`, `reservoir`, `tube`, `tip_rack`), format (1, 96, 384), name, labware_load_name, parent_barcode, location, status, created_at, meta (JSON) |
| `contents` (current state, one row per well) | container_id, well (primary key together), compound, concentration_value, concentration_unit, solvent, volume_ul, dead_volume_ul, lot, components (JSON: compound amounts in fmol, solvent and medium in µL), updated_at |
| `transfers` | id, run_id, command_id, step, src_container_id, src_well, dst_container_id, dst_well, volume_ul, started_at, finished_at, source (`sim`, `robot`, `manual`), operator, status. Unique on (run_id, command_id, src_well, dst_well) so replays are idempotent |
| `events` (append-only, never updated or deleted) | id, ts, run_id, container_id, well, action (`register`, `scan`, `aspirate`, `dispense`, `adjust`, `archive`, `note`), volume_ul, liquid, before (JSON), after (JSON), detail |
| `scans` | id, ts, barcode, container_id (null if unknown), ok, context |
| `counters` | kind, next_number (for generating barcodes such as `HH-STK-0001`) |

Semantics:
- **One transfer is one transaction:** check `source volume >= volume + dead volume` (refuse unless `allow_below_dead=True`), decrement the source, increment the destination, merge the destination's `components` with the well-mixed model, write an `aspirate` and a `dispense` event, write the transfer row. If the key `(run_id, command_id, src_well, dst_well)` exists, return the stored row and change nothing.
- **Well-mixed model:** removing V µL from a well removes the same fraction of every component. This is exactly what `_WellContents` does in `src/plan_checker.py` (read it, copy the idea, do not import its private class). Concentration of a compound in a well = fmol / µL = nM.
- **8-channel batches:** the caller records eight transfers that share a `command_id` (one per row), with the channel number in `detail`.
- **Lineage:** `get_lineage(barcode, well, direction)` walks the transfers graph (source to destination) with a depth limit.

## 3. Interface (the adapter a real LIMS would implement later)

A `Protocol` class `RegistryAdapter` and one implementation `SqliteRegistry`, in `src/registry.py`. Method names and fields (from the research sketch):

- `register_container(kind, format, barcode=None, name="", labware_load_name="", parent_barcode=None, location="", meta=None) -> Container` (generates `HH-<KIND>-<NNNN>` when no barcode is given)
- `register_content(container_barcode, well, compound, concentration_value, concentration_unit, solvent, volume_ul, dead_volume_ul=20.0, lot="", actor="")`
- `get_by_barcode(barcode, well=None)` returns the container with its wells, parents and children; `None` if unknown
- `list_wells(plate_barcode)` returns well, compound, concentration, solvent, volume
- `record_scan(barcode, context="") -> Container | None` (writes a `scans` row and a `scan` event)
- `record_transfer(run_id, command_id, src, dst, volume_ul, started_at=None, finished_at=None, source="sim", operator="", allow_below_dead=False) -> Transfer`
- `adjust_volume(barcode, well, delta_ul, reason, actor)` and `archive(barcode, reason, actor)`
- `get_lineage(barcode, well=None, direction="both", depth=5)` returns nodes and edges
- `get_history(barcode, well=None, since_event_id=0)` returns events in order
- `events_since(event_id, limit=500)` for the live view (a cursor, not a timestamp)
- `capabilities()` returns what this adapter supports (wells, volume, lineage, scan UI, label symbologies, audit)

## 4. Tasks, in priority order

### P0. Core and tests (target: done by about 11 PM)
1. `src/registry.py` with the schema, `RegistryAdapter` and `SqliteRegistry` as above. Pure standard library.
2. `tests/test_registry.py` (use a temp database per test): register a stock plate with 8 compounds, transfer decrements the source and increments the destination, a transfer below the dead volume is refused, replaying the same key changes nothing, events are append-only and ordered, lineage and history return what happened, two connections can write and read at the same time.
3. **Cross-check against the planner's checker:** build a registry from the example plate (see `src/planning.py`), replay the plan's transfers, and assert that every assay well's concentration and volume match what `check_plan` simulates, within 1e-3 relative. This is the test that proves the registry and the planner agree.

### P1. Labels, API, scan page
1. `src/registry_labels.py`: a Code 128 label as SVG with the barcode, its text and the container name. Use `python-barcode` (pure Python, SVG writer, no Pillow) if it installs cleanly on 3.12 with `uv add python-barcode`; otherwise write a small Code 128-B encoder and test it against known encodings. Label sheets can be printed from the browser, no printer driver.
2. `api/registry_routes.py` (a FastAPI router mounted at `/registry` with the smallest possible change in `api/app.py`; keep the existing loopback, Host and Origin checks): `GET /registry/containers`, `POST /registry/containers`, `GET /registry/containers/{barcode}`, `POST /registry/scan` (`{barcode, context}`; unknown barcode returns `{found: false}`, not an error), `POST /registry/transfers`, `GET /registry/containers/{barcode}/wells/{well}/history`, `GET /registry/containers/{barcode}/lineage`, `GET /registry/labels/{barcode}.svg`, `GET /registry/events?since=<id>` (the feed the live view polls every 0.5 s), `POST /registry/demo` (seed a demo set). Tests with `TestClient`.
3. A self-contained scan page served by the API at `GET /registry/scan-page`: one autofocused text input (a USB scanner types the code and presses Enter), posts to `/registry/scan`, shows the container card and a wells table, plus "mock scan" buttons for the demo barcodes. No external scripts or fonts. It must work with no scanner attached.

### P2. Bridge to the planner and the run
1. `src/registry_plan.py`:
   - `stocks_from_container(registry, barcode)` returns the planner's stocks (compound to `StockSolution`) and a map compound to stock well, from a scanned stock plate. Import `plate_layout.StockSolution`, do not change it.
   - `replay_plan(registry, plan, role_to_barcode, run_id, stock_wells, seconds_per_transfer=5.0)` feeds `plan.transfers` into `record_transfer` with `command_id=f"step-{t.step}"`, `source="sim"` and increasing timestamps. This is the simulation feed for the Live plates view. Labware roles (`stock`, `intermediate`, `assay`, `medium` or `reservoir`) are opaque strings mapped through `role_to_barcode`. Do not import the planner's role constants: a pending planner change renames the medium role and adds an `edge` phase, so treat unknown roles as a clear error.
2. `verify_deck(expected: dict[str, str], scanned: dict[str, str])` returns a list of mismatches (slot or role, expected barcode, scanned barcode). The run commands will use it to block a run when the wrong plate is loaded. Just the function and its tests for now.

### P3. CLI
`cli/registry.py` (Typer, add `registry = "cli.registry:app"` to `[project.scripts]`): `init`, `seed-demo`, `containers`, `show BARCODE`, `scan [BARCODE]` (reads a line from stdin when omitted, `--mock` accepted), `label BARCODE -o file.svg`, `history BARCODE WELL`, `transfer ...`.

### P4. Only if time remains
`from_run_commands(registry, commands, role_to_barcode)` turning the robot's per-command feed (`FlexClient.commands`, being added by `ebrinz`) into `record_transfer` calls keyed by `(run_id, command_id)`. An InvenTree adapter (see `GOALS.md` G6 for the pass/fail test).

## 5. Demo data

`seed-demo` creates: a stock plate (`HH-STK-0001`, 8 dye stand-ins in column 1, rows A to H, equal concentration, 1000 µL each), an empty intermediate deep-well plate, an empty assay plate, and a medium reservoir with one well of 15000 µL medium. Print the barcodes so the team can make labels.

## 6. Verification

```bash
cd drug-screen-platform
uv sync
uv run pytest                                   # includes tests/test_registry*.py
uv run registry init && uv run registry seed-demo
uv run registry scan HH-STK-0001 --mock
uv run registry label HH-STK-0001 -o runs/label.svg
uv run python scripts/serve.py                  # then open http://127.0.0.1:8000/registry/scan-page
```

Keep `tests/test_plan_checker.py` green. Verify the scan page by hand in a browser if you can, and say so in the report if you could not.

## 7. Acceptance checklist

- [ ] `uv run pytest` passes on Python 3.12, including the planner cross-check test
- [ ] A transfer is atomic, idempotent on `(run_id, command_id, src_well, dst_well)`, and refuses to go below the dead volume
- [ ] `events` is append-only and `GET /registry/events?since=<id>` returns only newer events
- [ ] `replay_plan` of the example plate leaves every assay well matching `check_plan`
- [ ] Label SVG renders and contains the barcode text; the scan page works with no scanner
- [ ] No secrets, IPs or serial numbers in the diff; loopback-only tests still pass

## 8. Report format

End with: files changed, the commands you ran with their real output (pass or fail), what you did not verify, and open questions. "Written, not tested" is an acceptable status for anything you could not run. Do not weaken or skip a test to make it pass.

## Out of scope

External LIMS adapters, camera scanning (browsers need HTTPS or localhost for camera access), label printer drivers, authentication, changes to the planner, the generator or the web app.
