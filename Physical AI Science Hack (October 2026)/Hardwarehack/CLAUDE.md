# Hardwarehack

Physical AI for Science Hack (San Francisco, Oct 2026), Track 3 (open track):
an end-to-end drug screening platform driving an Opentrons Flex.

## Layout

- `drug-screen-platform/` — Python 3.12, managed with uv: logic, web API and CLIs
  - `src/plate_formats.py` — plate geometry, well names, Opentrons labware load names
  - `src/plate_layout.py` — layout model (wells → drug, concentration, role), JSON/CSV
  - `src/dilution_planner.py` — intermediate dilutions and the ordered transfer list
  - `src/plan_checker.py` — replays the transfer list and checks every well (independent of the planner)
  - `src/planning.py` — plan + check in one call, well volume, materials, example plate
  - `src/protocol_generator.py` — transfer list → Opentrons Flex protocol (apiLevel 2.30, before/after camera images)
  - `src/flex_client.py` — Flex HTTP API client (port 31950) and `MockFlexClient`
  - `src/run_store.py` — `runs/<plate-slug>/`: layout, transfers, protocol, snapshots, run info (git-ignored)
  - `api/` — FastAPI app for the web UI; `cli/` — `plate` and `flex` commands
  - `tests/` — pytest (protocols are checked with the real Opentrons simulator)
- `drug-screen-platform/src/concoction.py` — per-column recipes from the 12-trough reservoir: rules, tip budget, protocol
- `drug-screen-platform/src/apothecary_state.py`, `api/apothecary.py` — console state (`runs/apothecary.json`) and routes
- `web/` — Next.js (App Router, TypeScript, Tailwind): the Athelas Apothecary concoction console
- `docs/superpowers/` — design spec and implementation plan for the web/API/CLI rewrite

## Commands

```bash
cd drug-screen-platform
uv sync
uv run pytest
uv run python scripts/serve.py          # API on 127.0.0.1:8000
FLEX_MOCK=1 uv run python scripts/serve.py --reload   # same, pretend robot + auto-reload (off the robot's network)
uv run plate check [plate.json]         # replay the plan (default: example plate)
uv run plate protocol plate.json        # generate runs/<plate>/protocol.py
uv run plate simulate runs/<plate>/protocol.py
uv run flex health --host <robot-ip>    # or set FLEX_HOST; --mock for a pretend robot
uv run flex demo plate.json --host <robot-ip>   # check → protocol → simulate → before → run → after
uv run flex calibrate --host <robot-ip>         # jog-measure the PCR plate height in B3 (riser!)
uv run flex fill --plate "Plate 1" --host <robot-ip>   # 8-channel medium fill, next free plate column

cd web
npm install
npm run dev                             # UI on http://127.0.0.1:3000 (proxies /api to :8000)
npm test && npm run lint && npm run build
```

Studio45 deck (medium fill): 1000 µL tips A1, 50 µL filter tips A2, 12-trough reservoir B1,
stock plate B2, Armadillo 96-well PCR plate seated on a 96 deep-well plate (riser) in B3, trash A3. The riser makes the plate's default
height wrong: runs carry the offsets from `flex calibrate` (`runs/labware_offsets.json`), and
`flex fill` refuses to run without one.

Any change to the planner must keep `tests/test_plan_checker.py` green (300 random layouts).
`web/lib/layout.ts` ports `PlateLayout.apply_dose_series`; keep the two in step (`web/lib/layout.test.ts`).

## Security

Both servers bind 127.0.0.1 only and the API drives a physical robot. Keep it that way:
the API rejects non-loopback `Host`/`X-Forwarded-Host` (DNS rebinding) and cross-site
`Origin`/`Sec-Fetch-Site` (CSRF), and validates robot host and run ids. User text that
goes into a generated protocol must be a `repr()` literal or pass `_comment_text`.

## Conventions

- Numpy-style docstrings and type hints; comments only where they explain *why*
- Descriptive names, no single-letter variables except loop indices
- try/except around file I/O and external calls
- Keep UI and logic separate: anything a robot protocol needs lives in `src/`, not in `api/`, `cli/` or `web/`
- Commit messages: conventional commits, short (e.g. `feat: add intermediate plate view`)
- Work on a branch (see below)

## Branching (3 contributors)

- Nobody pushes to `main` directly. Each of the three contributors works on and
  pushes to their own branch (e.g. `ebrinz`, `steffi/<topic>`), never to someone
  else's branch.
- Pull `main` into your branch often (`git fetch origin && git merge origin/main`)
  so conflicts stay small and get resolved on your branch, not on `main`.
- Merge your branch into `main` only when it is up to date with `origin/main`
  and `uv run pytest` is green. Merge locally, check the result, then push
  `main`. Prefer a fast-forward; if not possible, a plain merge commit is fine.
- Never force-push `main` or another contributor's branch.
