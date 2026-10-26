# Web UI, Python API and Flex CLI — design

Date: 2026-10-24. Status: draft for approval.

## Intent

Turn the drug screen designer from a CustomTkinter desktop app into three
pieces that run on any contributor's laptop (one Mac, two Windows) and reach
the Opentrons Flex at the hackathon:

1. a **Python backend** (FastAPI) on `127.0.0.1` that exposes the existing
   planner and checker plus a new Flex client;
2. a set of **CLI tools** (`plate`, `flex`) that call the same Python code
   directly, so the demo can be driven from a terminal without the browser;
3. a **Next.js web UI** on `127.0.0.1` that replaces the Tk GUI, including
   the full click-the-wells plate editor.

The Flex is driven over its HTTP API. The camera takes a **before** and an
**after** snapshot of the plate for each run.

The Claude Code Docker container and the Tk-specific code (fonts, canvas,
PyInstaller) go away.

## Why

- The Tk GUI only runs well on the Windows host it was written on and the
  Docker box was only there to give Windows users a Linux shell for Claude
  Code. A browser UI plus `uv` plus Node is the same on all three machines.
- The existing code stops at a transfer list. The hackathon entry needs the
  last mile: a protocol the Flex runs, and a camera picture that proves it.

## Goals

- Design a plate in the browser with the same features as today's Tk app
  (see "Plate editor" below).
- Generate an Opentrons Python protocol from a layout, simulate it locally,
  upload it to the Flex, start the run, and follow it to completion.
- Take a camera snapshot before and after the run and store both next to
  the layout file.
- Everything listens on loopback only so a host firewall can block the LAN.
- The three contributors can run it with `uv sync` and `npm install`.

## Non-goals

- Authentication, multi-user, or hosting anywhere but the laptop.
- Live camera streaming, or any vision analysis of the snapshots.
- A native desktop binary (PyInstaller) or the Windows icon.
- Replacing the planner, checker, layout model or their tests. They stay
  as they are and keep `tests/test_plan_checker.py` green.
- Randomized layouts, PubChem lookup (still roadmap).

## Anti-goals (would make this a failure even if it "works")

- A web UI that loses editor features the Tk app had (drag-select, dose
  series, legend, intermediate plate view).
- A backend that binds to `0.0.0.0` by default.
- A protocol generator that is not covered by the Opentrons simulator
  before it is ever sent to a real robot.

## Constraints

- Hackathon timeframe: October 2026, three people, parallel work.
- Robot: Opentrons Flex, robot software **10.1.0** (released 2026-10-15).
  Python Protocol API level 2.30 is the highest introduced (in 10.0.0);
  `capture_image()` needs 2.27+. The generated protocol uses
  `requirements = {"robotType": "Flex", "apiLevel": "2.30"}`.
- The `opentrons` PyPI package is 10.1.0 and requires Python >= 3.10, so it
  fits the existing uv project (`.python-version` is 3.11).
- Robot HTTP API on port 31950. Every request sends the header
  `Opentrons-Version: *` (the server requires a version header).
- The existing layout JSON format is the contract between editor, planner,
  CLI and backend. It does not change.

## Repository layout after the change

```
Hardwarehack/
├── CLAUDE.md, README.md                 (updated; container sections removed)
├── docs/superpowers/specs/              (this document)
├── drug-screen-platform/                Python: library, backend, CLI
│   ├── pyproject.toml                   deps: customtkinter removed; add fastapi,
│   │                                    uvicorn, httpx, opentrons, typer
│   ├── src/                             unchanged logic modules
│   │   ├── plate_formats.py  plate_layout.py  dilution_planner.py
│   │   ├── plan_checker.py   calculators.py   formatters.py
│   │   ├── protocol_generator.py        NEW: transfer list -> Flex protocol .py
│   │   ├── flex_client.py               NEW: HTTP client for the robot
│   │   └── run_store.py                 NEW: where layouts, protocols, snapshots live
│   ├── api/                             NEW: FastAPI app
│   │   ├── app.py                       create_app(), CORS for 127.0.0.1 only
│   │   ├── layouts.py  plans.py  robot.py
│   │   └── schemas.py                   pydantic models mirroring the dataclasses
│   ├── cli/                             NEW: typer apps
│   │   ├── plate.py                     `plate` command
│   │   └── flex.py                      `flex` command
│   ├── scripts/verify_plan.py           kept (thin wrapper, or folded into `plate check`)
│   └── tests/                           existing + new
├── web/                                 NEW: Next.js app
└── (removed) docker/, docker-compose.yml, scripts/start_claude.sh,
    drug-screen-platform/main.py, src/plate_canvas.py, src/ui_helpers.py,
    src/font_manager.py, assets/icon.ico, .gitattributes *.ico line
```

## The pieces

### 1. Python library additions (`src/`)

**`protocol_generator.py`** — `generate_protocol(layout, plan, settings) -> str`.
Emits a self-contained Opentrons Python protocol:

- `requirements = {"robotType": "Flex", "apiLevel": "2.30"}`, `metadata` with
  plate name and generation time.
- Deck: assay plate (layout's `opentrons_load_name`), intermediate 96
  deep-well plate, a tube rack for stocks and medium, Flex 50 µL and
  1000 µL single-channel pipettes (or 8-channel where the plan allows;
  builder's call, default single-channel), tip racks, trash chute. Slot
  assignments are constants at the top of the generated file so a human
  can edit them in the Opentrons App.
- The transfer list is embedded as a literal and replayed in order with
  `aspirate`/`dispense` (or `transfer`), choosing the pipette by volume.
- `protocol.capture_image(home_before=True, filename="before")` as the
  first command and `...filename="after"` as the last, so the robot also
  keeps its own pair of pictures with the run.
- Pure function; no I/O. The CLI and backend write it to disk.

**`flex_client.py`** — `FlexClient(host, port=31950)` using `httpx`:

- `health()`
- `upload_protocol(path) -> protocol_id` (`POST /protocols`, multipart)
- `create_run(protocol_id) -> run_id` (`POST /runs`, `{"data": {"protocolId": ...}}`)
- `play(run_id)`, `pause`, `stop` (`POST /runs/{id}/actions`, `{"data": {"actionType": "play"}}`)
- `run_status(run_id) -> dict` (`GET /runs/{id}`), `commands(run_id)`
- `wait_until_done(run_id, on_progress)` polling every 2 s
- `snapshot() -> bytes` — tries `POST /camera/capturePreviewImage` (Flex,
  JPEG, body = capture settings), falls back to `POST /camera/picture`.
- Every request sends `Opentrons-Version: *`. Errors raise `FlexError`
  with the robot's message.

The exact request bodies must be checked against the robot's own OpenAPI
spec at `http://<robot-ip>:31950/openapi.json` on the first day with the
robot; the client has a `--dry-run`/mock mode so the rest can be built
without it.

**`run_store.py`** — one folder per plate under `runs/<plate-name>/`:
`layout.json`, `transfers.csv`, `protocol.py`, `before.jpg`, `after.jpg`,
`run.json` (run id, status, timestamps). Both CLI and backend use it so
the browser can show snapshots taken from the terminal and vice versa.

### 2. FastAPI backend (`api/`)

Started with `uv run uvicorn api.app:app --host 127.0.0.1 --port 8000`.
Binding address is hard-coded to loopback in the start script; CORS allows
`http://127.0.0.1:3000` only (and `localhost:3000`).

| Method | Path | Does |
|---|---|---|
| GET | `/formats` | plate formats, labware names, Flex compatibility notes |
| GET/PUT | `/layouts/{name}` | load/save layout JSON in the run store |
| GET | `/layouts` | list saved layouts |
| POST | `/layouts/{name}/dose-series` | apply a dose series to a selection (server-side, uses `PlateLayout.apply_dose_series`) — *builder may do this client-side instead if simpler* |
| POST | `/plan` | body: layout + stocks + pipetting settings → `DilutionPlan` + `CheckReport` |
| POST | `/plan/transfers.csv` | same, as CSV download |
| POST | `/protocol` | body: layout name → writes `protocol.py`, returns its text and simulator result |
| POST | `/robot/snapshot` | `{tag: "before"|"after"}` → saves jpg, returns URL |
| GET | `/robot/health` | proxy of the Flex health |
| POST | `/robot/runs` | upload + create + play; returns run id |
| GET | `/robot/runs/{id}` | status + last commands |
| POST | `/robot/runs/{id}/{play,pause,stop}` | |
| GET | `/runs/{name}/files/{file}` | serve snapshots and protocol files |

Robot host/port come from `FLEX_HOST` / `FLEX_PORT` env or a `.env` file,
also settable from the UI's robot panel for the session.

Pydantic schemas mirror the existing dataclasses; conversion functions
live in `schemas.py` so `src/` stays free of web concerns.

### 3. CLI (`cli/`)

Typer apps installed as scripts via `pyproject.toml` (`[project.scripts]`):

```
plate check plate.json [--min-transfer 5] [--all]     # today's verify_plan.py
plate plan plate.json [--csv transfers.csv]            # print/export the plan
plate protocol plate.json [-o protocol.py]             # generate
plate simulate protocol.py                             # opentrons.simulate, print run log
flex health [--host IP]
flex snapshot --tag before|after [--plate NAME]
flex run protocol.py [--plate NAME] [--wait]           # upload, create, play, follow
flex status RUN_ID | flex pause RUN_ID | flex stop RUN_ID
flex demo plate.json                                   # check → protocol → simulate →
                                                       # snapshot before → run --wait →
                                                       # snapshot after
```

`flex demo` is the one-command path for the stage.

### 4. Next.js web UI (`web/`)

- Next.js (App Router, TypeScript), Tailwind, no component library.
  `npm run dev` binds to `127.0.0.1` (`next dev -H 127.0.0.1`), and a
  `next.config` rewrite proxies `/api/*` to `http://127.0.0.1:8000/*` so the
  browser only ever talks to its own origin.
- State: one client-side `PlateLayout` object (same shape as the JSON),
  edited locally; saved to the backend on Save. Planning and checking go
  through `/api/plan`.
- Dark theme matching the Tk app's look (see `docs/screenshot_*.png` in
  `drug-screen-platform`): header with plate name, format selector,
  New/Open/Save/Export; two tabs.

**Plate editor tab** (parity with the Tk app, all required):

- SVG plate map for 6–1536 wells; well color = drug, brightness = log
  concentration, ring = positive control, grey tones for vehicle/untreated/empty.
- Selection: click, drag rectangle, click/drag row and column headers,
  corner = select all, Ctrl/Cmd and Shift to add/remove, Delete empties,
  Ctrl/Cmd+A selects all.
- Right panel: Selection summary, Assign wells (role, drug, final conc +
  unit), Dose series (top conc, dilution factor, along rows / down columns).
- Legend per drug with well count and concentration range; hover shows
  well, drug, concentration. Status bar: wells assigned, drug count, labware.

**Stocks & worklist tab**:

- Pipetting settings (final volume, min transfer, intermediate transfer,
  dead volume) and per-drug stock rows (conc + unit, solvent).
- "Update plan" → tables for Assay plate, Intermediate plate, All transfers;
  Materials list; simulation check result (green/red).
- Export transfers CSV.

**Robot panel** (new, on the worklist tab or a third tab, builder's call):

- Robot host, health indicator.
- Buttons: Generate protocol (shows simulator result), Snapshot before,
  Run, Pause/Stop, Snapshot after. Run progress: status and last command.
- Shows the before/after images side by side when they exist.

### 5. Removals and doc updates

- Delete `docker/`, `docker-compose.yml`, `scripts/start_claude.sh`,
  `drug-screen-platform/main.py`, `src/plate_canvas.py`, `src/ui_helpers.py`,
  `src/font_manager.py`, `assets/icon.ico`; drop `customtkinter` and
  `pyinstaller` from `pyproject.toml`; drop the `*.ico` line from
  `.gitattributes`.
- `CLAUDE.md`: new layout, commands (`uv run uvicorn …`, `npm run dev`,
  `uv run plate …`, `uv run flex …`), remove container notes; keep the
  branching section.
- `README.md` in both places: features unchanged, install and run steps
  updated, roadmap trimmed. Screenshots replaced once the web UI exists.

## Verification

- `uv run pytest` stays green; add tests for `protocol_generator`
  (generated file simulates cleanly with `opentrons.simulate` for the
  built-in example plate and for a few random layouts from the existing
  test helpers) and for `flex_client` against a mocked HTTP server
  (`httpx.MockTransport`).
- Backend: pytest with `TestClient` for `/plan` round-trip and `/protocol`.
- Web: `npm run build` passes; manual check of the editor against the
  feature list above with the example 96-well plate.
- Loopback: `lsof -i -P | grep LISTEN` shows both servers on 127.0.0.1 only.
- Robot day: `flex health`, then `flex demo` on a water-only plate.

## Decisions already made (by the user)

- Web UI replaces the Tk GUI; full plate editor in the browser.
- Next.js served locally on 127.0.0.1, firewalled from the LAN.
- Backend is Python; CLI tools for the Flex.
- Camera: before and after still snapshots only.
- Remove the Docker container and the font manager.

## Calls made by the designer (override if you disagree)

- FastAPI + uvicorn + httpx + typer on the Python side; App Router +
  TypeScript + Tailwind, no UI kit, on the web side; `npm`, not pnpm.
- CLI calls the library directly, not the HTTP backend.
- Protocol embeds the transfer list and replays it; single-channel
  pipettes by default.
- Snapshots are taken from the laptop over HTTP (not only inside the
  protocol) so they work even if the protocol fails early. The protocol
  also calls `capture_image` for the robot's own record.
- Run artifacts live under `drug-screen-platform/runs/` (git-ignored).

## Calls made during the builder check (override if you disagree)

- **Robot hardware is constants, not input.** Checked against Studio45 on
  robot day: one Flex 8-channel 1000 µL pipette (left, 5 µL minimum), a
  gripper, trash bin in A3, no modules. The protocol uses the pipette through
  its front nozzle (`SINGLE`, `start="H1"`) with 50 µL tips up to 50 µL and
  1000 µL tips above. The simulator's collision checks fixed the deck: stocks
  B1, assay B2, intermediate B3, medium C2, tips D1-D3, rest of rows A and C
  empty (spare nozzles hang toward the back). Plans default to a 5 µL minimum
  transfer and the generator refuses anything smaller.
- **Tube map is derived.** Stock and solvent tubes are filled A1, B1, C1,
  D1, A2, … in order of first use in the transfer list. The map is printed
  as a comment block at the top of `protocol.py`, returned by the API and
  printed by the CLI so the person loading the rack sees it.
- **Assay plate is pre-filled by hand**, as the planner already assumes
  (cells in medium at `volume − transfer`). The protocol adds only the
  planned transfers. Untreated wells get nothing.
- **Final well volume is saved** as `pipetting.well_volume_ul` in the layout
  JSON. This is an additive key that older code ignores, so files stay
  compatible. API and CLI plan with that value, falling back to the
  format's working volume.
- **No labware offsets.** Runs created over HTTP use nominal positions. Fine
  for a 96-well water demo; run Labware Position Check in the Opentrons
  App and start from there if accuracy matters. Offsets via HTTP are a
  follow-up.
- **Python 3.12.** `opentrons` 10.1.0's simulator fails to import on 3.11
  with current pydantic, so the project moves to 3.12.
- **One run folder per plate.** A rehearsal overwrites the previous
  snapshots of the same plate.

## Left to the builder

- Exact Flex HTTP request/response shapes (verify against
  `/openapi.json` on the robot; keep the mock mode until then).
- Deck slot layout, tip rack choice, whether to use `transfer()` with
  `new_tip` strategies or explicit aspirate/dispense.
- Whether dose series is computed client-side or via the endpoint.
- Component structure of the editor; SVG vs. canvas (SVG recommended for
  hit-testing and hover).
- How the Materials list and warnings are rendered.
