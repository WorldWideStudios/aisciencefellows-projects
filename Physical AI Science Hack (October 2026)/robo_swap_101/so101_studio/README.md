# Sequence Studio backend

Sequence Studio runs a loopback Python HTTP server and a serialized robot control
loop. Start it from the repository root with `python -m so101_studio` after
building `robot_viewer/`. Simulation uses Python's standard library; physical
connections require the LeRobot environment in the root README.

See the [operator guide](../robot_viewer/README.md) for teaching, planning,
playback, calibration, and Stop behavior.

## Source map

| Module | Responsibility |
| --- | --- |
| `server.py` | HTTP API, static UI serving, origin/token guards, command-line options |
| `runtime.py` | Control ownership, motion loop, recording, plan lifecycle, watchdogs |
| `devices.py` | Simulation, USB identity discovery, calibrated limits, hardware adapter |
| `model.py` | Input validation and atomic sequence storage with revision checks |
| `filtering.py` | Target smoothing shared with the standalone teleoperation launcher |
| `planner.py` | Joint trajectories, Cartesian pickup curves, timing and bounds |
| `kinematics.py` | URDF-based forward and inverse kinematics |

Browser trajectory evaluation lives in `robot_viewer/src/motion.js`. Keep it in
agreement with the Python planner; regression tests compare their results.

## Server options

Run `python -m so101_studio --help` for the command-line reference.

| Option | Default / purpose |
| --- | --- |
| `--port` | `8766`, bound to `127.0.0.1` |
| `--enable-hardware` | Permits an explicit browser connection; startup stays simulated |
| `--arms` | Repository `arms.json`, including exact USB serials and calibration IDs |
| `--data` | Repository `data/sequences.json`, the autosaved sequence library |
| `--web` | Repository `robot_viewer/dist`, built static browser assets |
| `--dev-origin` | Optional allowed loopback Vite origin for browser development |

For frontend development, start the backend with
`--dev-origin http://127.0.0.1:5173` and run `npm run dev` inside `robot_viewer/`
in another terminal. Open port 5173; Vite proxies the API to port 8766.

## Data and tests

The sequence library is local and ignored by Git. Export it through the browser
or back up the file before replacing a setup. Calibration files belong to the
LeRobot installation; `arms.json` references their IDs and does not contain them.

From the repository root, with browser dependencies installed:

```sh
.venv/bin/python -m unittest discover -s tests -v
cd robot_viewer
npm run build
```

Tests cover planner bounds, browser/server curve agreement, storage revisions,
recording, ownership, watchdogs, API guards, fake hardware adapters, and VIAFLO
protocol behavior. They do not open real robot buses. A passing suite does not
validate physical clearances, calibration accuracy, or load capacity.

Connection is gated by exact USB identity and existing calibration. Do not run
another serial controller against the same arms. Stop holds the follower in
software; disconnect and shutdown preserve torque. Support the arm before using
the explicit torque-release action. No collision checking is implemented.
