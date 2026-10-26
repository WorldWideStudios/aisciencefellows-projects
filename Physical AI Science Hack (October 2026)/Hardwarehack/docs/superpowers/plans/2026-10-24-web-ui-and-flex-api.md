# Web UI, Python API and Flex CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the CustomTkinter app and Docker box with a loopback-only FastAPI backend, `plate`/`flex` CLIs, a Flex protocol generator with camera snapshots, and a Next.js plate editor.

**Architecture:** Existing `src/` logic stays as flat top-level modules. New `src/` modules add protocol generation, a Flex HTTP client and a run store. `api/` (FastAPI) and `cli/` (typer) are thin layers over `src/`. `web/` (Next.js) talks only to its own origin; `/api/*` is rewritten to the backend on 127.0.0.1:8000.

**Tech Stack:** Python 3.11, uv, hatchling, FastAPI, uvicorn, httpx, typer, opentrons 10.1.0 (simulator), pytest; Next.js (App Router, TypeScript), Tailwind, npm.

**Spec:** `docs/superpowers/specs/2026-10-24-web-ui-and-flex-api-design.md`

## Global Constraints

- Both servers bind `127.0.0.1` only: uvicorn `--host 127.0.0.1 --port 8000`, `next dev -H 127.0.0.1 -p 3000`.
- CORS origins: `http://127.0.0.1:3000`, `http://localhost:3000` only.
- Generated protocol: `requirements = {"robotType": "Flex", "apiLevel": "2.30"}`.
- Robot HTTP port 31950; every robot request sends header `Opentrons-Version: *`.
- `FLEX_HOST` / `FLEX_PORT` env vars configure the robot; no host means mock mode is required to be explicit (`--mock`/`FLEX_MOCK=1`).
- Layout JSON format (`PlateLayout.to_dict`) does not change.
- `tests/test_plan_checker.py` stays green.
- Run artifacts live in `drug-screen-platform/runs/<slug>/` and are git-ignored.
- Conventions from CLAUDE.md: numpy docstrings, type hints, try/except around file I/O and external calls, conventional commits.

## Review Focus

1. **Plate names with spaces/slashes/unicode** ("Ferroptosis screen 1", "a/b") must map to a safe folder slug; test in Task 3.
2. **Robot unreachable or returns non-2xx** must give a one-line error, not a traceback, in CLI and a 502 JSON in the API; test in Tasks 4 and 6.
3. **Layout with no drugs / only untreated wells** must generate a protocol that simulates (only snapshots, no transfers); test in Task 2.
4. **1536-well layout** (no Opentrons labware) must be refused by protocol generation with a clear message; test in Task 2.
5. **Stock tubes for many drugs**: more distinct stock liquids than a 24-tube rack holds must be refused clearly; test in Task 2.

---

### Task 1: Remove Tk app and container; make the package installable

**Files:**
- Delete: `docker/`, `docker-compose.yml`, `scripts/start_claude.sh`, `drug-screen-platform/main.py`, `src/plate_canvas.py`, `src/ui_helpers.py`, `src/font_manager.py`, `assets/icon.ico`
- Modify: `drug-screen-platform/pyproject.toml`, `.gitattributes`, `drug-screen-platform/.gitignore`
- Modify: `tests/*.py` (drop `sys.path` hacks only if pytest `pythonpath` makes them redundant; leaving them is fine)

- [ ] Step 1: Delete the files above; remove `*.ico binary` from `.gitattributes`; add `runs/` to `.gitignore`.
- [ ] Step 2: `pyproject.toml`: deps `fastapi`, `uvicorn[standard]`, `httpx`, `typer`, `python-multipart`; dev group `pytest`, `opentrons==10.1.0`; remove `customtkinter`, `pyinstaller`. Build backend hatchling with `[tool.hatch.build.targets.wheel] packages = ["api", "cli"]` plus `sources`/`force-include` so `src/*.py` install as top-level modules. `[project.scripts] plate = "cli.plate:app"`, `flex = "cli.flex:app"`. `[tool.pytest.ini_options] pythonpath = ["src", "scripts", "."]`.
- [ ] Step 3: Run `uv sync && uv run pytest -q`. Expected: all existing tests pass.
- [ ] Step 4: Commit `chore: remove Tk GUI and Docker container, add web/api deps`.

### Task 2: Protocol generator

**Files:** Create `src/protocol_generator.py`, `tests/test_protocol_generator.py`

**Interfaces:**
- Produces: `generate_protocol(layout: PlateLayout, plan: DilutionPlan) -> str`; `class ProtocolError(ValueError)`; `DECK: dict[str, str]` (slot constants).
- Consumes: `plan.transfers` (`Transfer.source_labware` in `{"stock","medium","intermediate"}`, `dest_labware` in `{"intermediate","assay"}`; stock `source_well` is the liquid name, medium `source_well` is `"reservoir"`), `INTERMEDIATE_LABWARE`, `layout.plate_format.opentrons_load_name`.

Deck (constants at top of generated file): assay plate C2, intermediate `nest_96_wellplate_2ml_deep` B2, stock rack `opentrons_24_tuberack_nest_1.5ml_snapcap` C1, medium `nest_1_reservoir_195ml` D2, tips `opentrons_flex_96_tiprack_50ul` A2 and `opentrons_flex_96_tiprack_1000ul` B3, `flex_1channel_50` left, `flex_1channel_1000` right, trash `A3`. Stock liquids map to tube wells A1, B1, C1, D1, A2, … in order of first use (column-major). Pipette: volume ≤ 50 µL → 50 µL pipette, else 1000 µL. New tip per transfer. Transfers > pipette max are split into equal parts.

- [ ] Step 1: Tests: `test_example_protocol_simulates` (example layout → `opentrons.simulate.simulate(io.StringIO(text), "protocol.py")` returns without raising); `test_capture_image_first_and_last` (`"capture_image"` appears twice; `filename="before"` precedes the first `aspirate`, `filename="after"` follows the last `dispense`); `test_requirements_api_level` (`'"apiLevel": "2.30"'` in text); `test_empty_layout_simulates`; `test_1536_refused` (raises `ProtocolError` matching "no Opentrons labware"); `test_too_many_stocks_refused` (25 drugs → `ProtocolError` matching "24").
- [ ] Step 2: Run, expect import failure.
- [ ] Step 3: Implement. The generated file embeds `TRANSFERS = [...]` tuples and a `STOCK_TUBES = {...}` dict and replays them in `run(protocol)`.
- [ ] Step 4: `uv run pytest tests/test_protocol_generator.py -q` → pass.
- [ ] Step 5: Commit `feat: generate Flex protocol with before/after camera images`.

### Task 3: Run store

**Files:** Create `src/run_store.py`, `tests/test_run_store.py`

**Interfaces:**
- Produces: `RUNS_DIR: Path` (`<package root>/runs`, overridable via `RUNS_DIR` env), `slugify(name: str) -> str`, `class RunStore(root: Path = RUNS_DIR)` with `folder(plate: str) -> Path` (creates), `save_layout(layout) -> Path`, `load_layout(plate) -> PlateLayout`, `list_plates() -> list[str]`, `write_file(plate, filename, data: bytes|str) -> Path`, `path(plate, filename) -> Path` (raises `FileNotFoundError`; refuses names containing `/` or `..` with `ValueError`), `save_run_info(plate, info: dict)`, `load_run_info(plate) -> dict`.

- [ ] Step 1: Tests: `slugify("Ferroptosis screen 1") == "ferroptosis-screen-1"`, `slugify("a/b") == "a-b"`, `slugify("") == "untitled"`; round trip save/load layout in `tmp_path`; `path(plate, "../x")` raises `ValueError`.
- [ ] Step 2–4: fail, implement, pass.
- [ ] Step 5: Commit `feat: add run store for layouts, protocols and snapshots`.

### Task 4: Flex HTTP client

**Files:** Create `src/flex_client.py`, `tests/test_flex_client.py`

**Interfaces:**
- Produces: `class FlexError(RuntimeError)`; `class FlexClient(host: str, port: int = 31950, transport: httpx.BaseTransport | None = None, timeout: float = 30)` with `health() -> dict`, `upload_protocol(path: Path) -> str`, `create_run(protocol_id: str) -> str`, `action(run_id: str, action: Literal["play","pause","stop"]) -> None`, `run_status(run_id) -> dict` (returns `data`), `wait_until_done(run_id, on_progress: Callable[[dict], None] | None = None, poll_s: float = 2.0) -> dict` (terminal statuses `succeeded`, `failed`, `stopped`), `snapshot() -> bytes`; `class MockFlexClient` with the same methods (health ok, ids `"mock-protocol"`/`"mock-run"`, status succeeds immediately, snapshot returns a generated 1×1 JPEG); `client_from_env(mock: bool = False) -> FlexClient | MockFlexClient` reading `FLEX_HOST`, `FLEX_PORT`, `FLEX_MOCK`.
- Endpoints: `GET /health`; `POST /protocols` multipart field `files`, id at `data.id`; `POST /runs` body `{"data": {"protocolId": id}}`, id at `data.id`; `POST /runs/{id}/actions` body `{"data": {"actionType": action}}`; `GET /runs/{id}`; snapshot `POST /camera/capturePreviewImage` body `{"data": {}}`, on 404/405/422 fall back to `POST /camera/picture`.

- [ ] Step 1: Tests with `httpx.MockTransport`: header `Opentrons-Version` sent on every call; upload returns id; play posts correct body; snapshot falls back on 404; connection error → `FlexError` whose message contains the host; 500 with `{"errors":[{"detail":"boom"}]}` → `FlexError` containing `boom`; `wait_until_done` returns on `succeeded` and calls `on_progress`.
- [ ] Step 2–4: fail, implement, pass.
- [ ] Step 5: Commit `feat: add Flex HTTP client with mock mode`.

### Task 5: CLI (`plate`, `flex`)

**Files:** Create `cli/__init__.py`, `cli/plate.py`, `cli/flex.py`, `tests/test_cli.py`; modify `scripts/verify_plan.py` (keep `example_layout`, make `main()` delegate to the shared check printer in `cli/plate.py`).

**Interfaces:** consumes Tasks 2–4. `plate check [LAYOUT] [--volume] [--min-transfer] [--all]` (no LAYOUT = example plate; exit 1 on fail), `plate plan LAYOUT [--csv PATH]`, `plate protocol LAYOUT [-o PATH]` (default writes into run store), `plate simulate PROTOCOL`, `flex health`, `flex snapshot --tag before|after --plate NAME`, `flex run PROTOCOL [--plate NAME] [--wait/--no-wait]`, `flex status|pause|stop RUN_ID`, `flex demo LAYOUT`. All `flex` commands accept `--host`, `--port`, `--mock`. `FlexError`/`ProtocolError`/`OSError` print `Error: <msg>` and exit 2.

- [ ] Step 1: Tests via `typer.testing.CliRunner`: `plate check` exits 0 and prints `PASSED`; `plate protocol <tmp layout> -o out.py` writes a file containing `capture_image`; `flex demo <layout> --mock` with `RUNS_DIR=tmp` exits 0 and leaves `before.jpg`, `after.jpg`, `protocol.py`, `run.json` in the run folder; `flex health --host 127.0.0.1 --port 1` exits 2 with `Error:`.
- [ ] Step 2–4: fail, implement, pass. Also `uv run plate check` and `uv run flex demo --mock` work from the shell.
- [ ] Step 5: Commit `feat: add plate and flex CLIs`.

### Task 6: FastAPI backend

**Files:** Create `api/__init__.py`, `api/app.py` (`create_app() -> FastAPI`, module-level `app`), `api/schemas.py`, `api/routes.py`, `tests/test_api.py`, `scripts/serve.py` (runs uvicorn on 127.0.0.1:8000).

Routes (no `/api` prefix; Next rewrites strip it): `GET /formats`; `GET /layouts`; `GET /layouts/{plate}`; `PUT /layouts/{plate}` (body = layout dict); `POST /plan` (body `{layout, volume_ul?}` → `{plan, check, materials}`, `volume_ul` default = format working volume, settings from `layout.pipetting`); `POST /plan/transfers.csv`; `POST /protocol` (body `{layout}` → saves layout + protocol, returns `{plate, protocol, simulation: {ok, log|error}}`; simulation only if `opentrons` importable); `GET /robot/health`; `POST /robot/snapshot` `{plate, tag}` → `{url}`; `POST /robot/runs` `{plate}` → upload `protocol.py`, create, play, save `run.json`, return `{run_id}`; `GET /robot/runs/{run_id}`; `POST /robot/runs/{run_id}/{action}`; `GET /files/{plate}/{filename}`; `GET/PUT /robot/config` `{host, port, mock}` (session-level override of env). `FlexError` → 502 `{"detail": msg}`; `ProtocolError`/`ValueError` → 422.

- [ ] Step 1: Tests with `TestClient`: `/formats` lists `96-well` with load name; `/plan` with example layout returns `check.passed == true` and 120 transfers; `/protocol` returns text containing `apiLevel`; with `/robot/config` mock true, `/robot/snapshot` then `GET` its url returns `image/jpeg`; robot unreachable (`host 127.0.0.1 port 1`) → 502; CORS preflight from `http://evil.com` gets no `access-control-allow-origin`.
- [ ] Step 2–4: fail, implement, pass.
- [ ] Step 5: Commit `feat: add loopback FastAPI backend`.

### Task 7: Next.js app shell and layout model

**Files:** Create `web/` via `create-next-app` (TypeScript, Tailwind, App Router, no src dir, npm). `web/next.config.ts` rewrites `/api/:path*` → `http://127.0.0.1:8000/:path*`. `package.json` scripts: `dev: next dev -H 127.0.0.1 -p 3000`, `start: next start -H 127.0.0.1 -p 3000`. Create `web/lib/layout.ts`, `web/lib/api.ts`, `web/lib/wells.ts`, `web/lib/layout.test.ts` (vitest).

**Interfaces (produced):**
- `wells.ts`: `rowLabel(i)`, `wellName(r,c)`, `parseWell(name) -> [r,c]`, `FORMATS` fetched list type `PlateFormat {name, rows, columns, max_volume_ul, default_working_volume_ul, opentrons_load_name}`.
- `layout.ts`: types `WellAssignment`, `StockSolution`, `Layout` matching `to_dict`; pure functions `assign(layout, wells, a)`, `clearWells(layout, wells)`, `applyDoseSeries(layout, wells, drug, top, unit, factor, role, alongRows)` (port of `PlateLayout.apply_dose_series`, same `.4g` rounding), `drugs(layout)`, `changeFormat(layout, format)`, `toNanomolar`.
- `api.ts`: typed wrappers for every Task 6 route.

- [ ] Step 1: vitest tests: `applyDoseSeries` on `A2..A11` top 20 µM factor 2 matches Python output for the example plate (A2=20, A3=10, A11=0.03906); `wellName(26,0) == "AA1"`.
- [ ] Step 2–4: fail, implement, pass (`npx vitest run`).
- [ ] Step 5: Commit `feat: scaffold Next.js app with layout model`.

### Task 8: Plate editor tab

**Files:** Create `web/app/page.tsx`, `web/components/Header.tsx`, `PlateMap.tsx`, `EditorPanel.tsx`, `Legend.tsx`, `StatusBar.tsx`, `web/lib/colors.ts`.

Parity list (all required): SVG plate 6–1536 wells; color = drug palette, brightness = log concentration within drug range, ring = positive control, greys for vehicle/untreated/empty; click, drag rectangle, row/column header click and drag, corner selects all, Ctrl/Cmd toggles, Shift adds; Delete empties, Ctrl/Cmd+A selects all (not while typing in inputs); selection summary; Assign (role, drug, conc, unit) and Empty; Dose series (top, unit, factor, along rows/down columns); legend with count and range; hover readout; status bar (assigned/total, drug count, labware); header: plate name, format buttons (confirm if wells would be dropped), New, Open (list from `/api/layouts` + file upload), Save, Export layout CSV (client-side). Dark theme close to `drug-screen-platform/docs/screenshot_96well.png`.

- [ ] Step 1: `npm run build` passes; `npm run lint` passes.
- [ ] Step 2: Manual check in browser against the parity list with the example plate.
- [ ] Step 3: Commit `feat: browser plate editor`.

### Task 9: Stocks & worklist tab and robot panel

**Files:** Create `web/components/WorklistTab.tsx`, `PlanTables.tsx`, `RobotPanel.tsx`.

Worklist: pipetting fields (final volume, min transfer, intermediate transfer, dead volume) stored in `layout.pipetting`; stock rows per drug (conc, unit, solvent) stored in `layout.stocks`; Update plan → `/api/plan`; tables Assay plate / Intermediate plate / All transfers; materials; check result green/red; Export transfers CSV. Robot panel: host/port/mock fields (`/api/robot/config`), health dot, buttons Generate protocol (shows simulation ok/error), Snapshot before, Run, Pause, Stop, Snapshot after; polls `/api/robot/runs/{id}` every 2 s while active; before/after images side by side.

- [ ] Step 1: `npm run build` passes.
- [ ] Step 2: Manual end-to-end with backend in mock mode: plan passes, protocol simulates, before/run/after completes and both images show.
- [ ] Step 3: Commit `feat: worklist tab and robot panel`.

### Task 10: Docs and loopback check

**Files:** Modify `CLAUDE.md`, `README.md`, `drug-screen-platform/README.md`; mark spec decisions.

- [ ] Step 1: Update layout, commands (`uv run python scripts/serve.py`, `npm run dev`, `uv run plate …`, `uv run flex …`), remove container notes, keep branching section; firewall note (both servers loopback only; allow outbound to the Flex on 31950).
- [ ] Step 2: Start both servers; `lsof -nP -iTCP -sTCP:LISTEN | grep -E ':(3000|8000)'` shows only `127.0.0.1`.
- [ ] Step 3: `uv run pytest -q` and `npm run build` green.
- [ ] Step 4: Commit `docs: update for web UI, API and Flex CLI`.
