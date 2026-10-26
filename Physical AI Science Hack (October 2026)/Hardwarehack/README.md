# Hardwarehack

Physical AI for Science Hack (San Francisco, Oct 2026), Track 3: an end-to-end
drug screen on the Opentrons Flex. Design a plate in the browser, plan the
dilutions, generate and simulate the Flex protocol, then run it with a camera
snapshot of the deck before and after.

## Projects

- [`drug-screen-platform/`](drug-screen-platform/): Python planner, protocol
  generator, Flex client, web API and the `plate` / `flex` command-line tools
- [`web/`](web/): Next.js plate editor, worklist and robot control

## Requirements

- [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you; the Opentrons
  package does not import on 3.11)
- Node.js 20 or newer
- For the robot: your laptop on the same network as the Flex, **with any VPN
  turned off** (a VPN can block local devices)

## Spin up the UI

The dashboard is two local servers: a Python API and the Next.js web app.
Open two terminals in the repo root (the same commands work in macOS Terminal
and Windows PowerShell).

```bash
# terminal 1: API on 127.0.0.1:8000
cd drug-screen-platform
uv sync                          # first time, and after pulling new dependencies
uv run python scripts/serve.py

# terminal 2: web UI on 127.0.0.1:3000
cd web
npm install                      # first time, and after pulling new dependencies
npm run dev
```

Then open <http://127.0.0.1:3000>. Keep both terminals running; Ctrl-C stops
each server.

To connect the robot, click the robot button at the top right of the console,
enter the robot's IP address and press **Connect**. To have the API connect on
start instead:

```bash
FLEX_HOST=<robot-ip> uv run python scripts/serve.py          # macOS / Linux
$env:FLEX_HOST="<robot-ip>"; uv run python scripts/serve.py  # Windows PowerShell
```

### Working without the robot (mock mode)

Away from the lab, or off the robot's Wi-Fi, run the API against a pretend
robot. Everything works the same except that nothing physical moves:

```bash
cd drug-screen-platform
FLEX_MOCK=1 uv run python scripts/serve.py --reload                   # macOS / Linux
$env:FLEX_MOCK="1"; uv run python scripts/serve.py --reload           # Windows PowerShell
```

- The header shows **Mock robot**. You can also switch while the API runs: click
  the robot button, tick **Mock robot** and press **Connect** (this lasts until
  the API restarts).
- Orders are still checked and run through the Opentrons simulator. **Brew**
  "runs" instantly on the mock and the camera returns a placeholder picture.
- Brewing on the mock is still recorded: trough volumes go down, tip columns are
  used and plate columns are marked brewed (in `runs/apothecary.json`). Use
  **Tip racks refilled** and **New plate** to reset, or point the API at a
  scratch folder so your real records stay untouched:
  `RUNS_DIR=/tmp/athelas-mock FLEX_MOCK=1 uv run python scripts/serve.py --reload`.
- `--reload` restarts the API by itself whenever Python code changes; without
  it, restart the API after pulling or editing Python code.
- The command-line tools take `--mock` the same way, e.g.
  `uv run flex demo plate.json --mock`.

Back at the robot, start the API without `FLEX_MOCK` (and turn any VPN off).

The web UI is the **Athelas Apothecary** console, a concoction-on-demand screen
for the Studio45 deck:

- **Reservoir:** name the 12 troughs in B1, pick their colours and set how many
  mL each holds.
- **Plate:** pick a column of the Armadillo plate in B3. Every well in the
  column (A-H) gets the same recipe, because the 8-channel fills a whole column.
- **Recipe:** add ingredients from the troughs, at least 5 µL each and at most
  200 µL per well in total. Each draw uses a fresh column of tips (50 µL filter
  tips up to 50 µL, 1000 µL tips above), and the last tip mixes the well.
- **Order:** the console checks the order and runs it through the Opentrons
  simulator as you edit; **Brew** sends it to the robot (or the mock) and keeps
  track of trough volumes, tip columns and brewed columns.

The older drug-screen plate designer is still available from the command line
(`plate` and `flex demo`).

Both servers listen on 127.0.0.1 only, so nothing is reachable from the LAN.
If you also run a host firewall, block inbound connections on 3000 and 8000
and allow outbound TCP 31950 to the robot.

**Troubleshooting**

- *"Backend not reachable"* in the browser: terminal 1 isn't running, or it
  stopped with an error.
- *"Can't reach the Flex at ..."*: check the IP on the robot's touchscreen
  (Settings, Network), put the laptop on the same network, turn the VPN off.
- *Port already in use*: an old server is still running; close its terminal,
  or stop it with `pkill -f scripts/serve.py` / `pkill -f "next dev"`.
- *The UI shows old data or names*: the API is running old code; restart it
  (or run it with `--reload`).
- *The page looks half styled or stale*: stop `npm run dev`, delete `web/.next`
  and start it again.
- `npm` says it can't find `package.json`: you are not in the `web` folder.

## Command line

All commands run from `drug-screen-platform`. The robot commands need the
robot's address: pass `--host <robot-ip>` each time, or set `FLEX_HOST` once
(as above). `--mock` uses a pretend robot.

```bash
cd drug-screen-platform
uv run flex health --host <robot-ip>     # first thing to run at the robot
```

### Plates and protocols (`plate`, no robot needed)

| Command | What it does |
|---|---|
| `uv run plate check [plate.json]` | Replay the pipetting plan and check every well (no file: built-in example plate) |
| `uv run plate plan plate.json [--csv transfers.csv]` | Print the ordered transfer list, or export it |
| `uv run plate protocol plate.json` | Generate `runs/<plate>/protocol.py` and print the stock tube map |
| `uv run plate simulate runs/<plate>/protocol.py` | Run a protocol through the Opentrons simulator |

`plate.json` is a layout saved from the web UI (it lands in
`runs/<plate>/layout.json`).

### The robot (`flex`)

| Command | What it does |
|---|---|
| `uv run flex health` | Robot name, model and software version |
| `uv run flex snapshot --plate NAME --tag before` | Deck camera picture into `runs/<plate>/before.jpg` |
| `uv run flex calibrate` | Measure the real height of the PCR plate on its riser (see below) |
| `uv run flex fill --plate NAME --volume 40` | 8-channel medium fill into the next free plate column |
| `uv run flex run runs/<plate>/protocol.py --plate NAME` | Upload a protocol, start it and follow it to the end |
| `uv run flex status RUN_ID` / `pause RUN_ID` / `stop RUN_ID` | Control a run |
| `uv run flex demo plate.json` | Check, generate, simulate, before picture, run, after picture |

Every command has `--help`. `flex fill` simulates its protocol and asks before
starting (`--yes` skips the question); `flex demo` simulates before running;
`flex run` starts the file you give it straight away, so simulate it first with
`plate simulate`.

### Medium fill on the Studio45 deck

Deck: 1000 µL tips in A1, 50 µL filter tips in A2, 12-trough reservoir in B1
(medium in trough 1), stock plate in B2, Armadillo 96-well PCR plate seated on a
96 deep-well plate (the riser) in B3, trash in A3. Take the lids off the tip
boxes.

1. **Calibrate the plate height** (once, and again whenever the plate or riser
   is reseated). The riser makes the default height wrong; without this the
   tips are driven into the plate, and `flex fill` refuses to run.

   ```bash
   uv run flex calibrate --host <robot-ip>
   ```

   The robot picks up tips from column 12 of the 50 µL rack and stops 80 mm
   above where it expects the plate. At the `jog:` prompt type `d 10`, `d 1`,
   `d 0.1` (down), `u 1` (up), `x 0.5` / `y 0.5` (sideways) and press Enter,
   until the tip ends are level with the well tops. Type `ok`, then `y` to
   save; `q` aborts. The tips go back to the rack and the robot homes either
   way. Expect a z offset of about 35-41 mm. Run this in a normal terminal,
   not through `!` in Claude Code (the prompt can't read input there).

2. **Fill.** Each fill takes the next tip column and the next free plate
   column, and logs them in `runs/<plate>/fills.json`:

   ```bash
   uv run flex fill --plate "Plate 1" --host <robot-ip> --volume 40
   uv run flex fill --plate "Plate 1" --host <robot-ip> --volume 40 --position 1 --tip-column 2   # choose explicitly
   ```

   The 50 µL tips limit a fill to 5-50 µL per well. After 12 fills the tip
   rack is used up; the command tells you when to replace it.

### Where files go

Everything a run produces is in `drug-screen-platform/runs/` (not in git):
layouts, protocols, transfer lists, camera pictures, `fills.json`, and the
plate calibration in `labware_offsets.json`. Calibrations are per laptop:
each laptop that runs fills needs its own `flex calibrate`.
