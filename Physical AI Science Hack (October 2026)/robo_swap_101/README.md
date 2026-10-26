# robo_swap_101

SO-101 leader/follower teleoperation experiments and a prototype quarter-turn tool swapper for the follower wrist.

The project includes a local browser-based Sequence Studio, Python helpers for calibration and teleoperation, VIAFLO pipettor control, recorded diagnostics, and CAD prototypes with STEP/STL exports and drawings.

![Tool swapper assembly and sequence](design/tool_swapper_v1/diagrams/01_assembly_and_sequence.png)

## Project contents

| Path | Purpose |
| --- | --- |
| `arms.json` | Recorded leader/follower USB identities, macOS serial ports, and calibration IDs |
| `calibrate_arm.py` | Calibrate one arm after connecting the bus and disabling torque |
| `teleoperate_arms.py` | LeRobot launcher with target smoothing, speed limits, and bounded write retries |
| `diagnose_teleop.py` | Instrument teleoperation and save timing, observations, and actions |
| `diagnostics/`, `diagnostics_startup.txt` | Recorded diagnostic output from local experiments |
| `calibration_backups/` | Historical calibration backup; the included follower file is incomplete |
| `design/tool_swapper_v1/` | Original interrupted-screw coupling, pin lock, rack, CAD, and validation |
| `design/tool_swapper_v2/` | Single-orientation keyhole coupling with three flared dowels, CAD, and validation |
| `design/tool_swapper_v3/` | Fitted SO-101 male and 31 mm pipette collar |
| `design/tool_swapper_v3_thin_wall/` | Reinforced male compatible with the fitted v3 collar |
| `design/tool_swapper_v4_flared_pipette/` | Flared-dowel coupling with a compact pipette receiver and 5 mm spacer |
| `robot_viewer/` | Sequence Studio browser UI and standalone model explorer |
| `so101_studio/` | Local Python server, persistence, trajectory planner, and hardware adapters |
| `tools/viaflo/`, `viaflo_control.py` | VIAFLO terminal controller and native macOS Bluetooth transport |
| `tests/` | Hardware-free Studio and VIAFLO regression tests |

## Robot setup

The local robot environment used Python 3.12 and LeRobot 0.6.1. Create an isolated environment and install the robot dependencies:

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
```

Before running hardware, identify your own serial devices and calibration IDs. Sequence Studio loads the role assignments in `arms.json`; these now match follower `5A7A055478` and leader `5A7A056103`. The standalone calibration and teleoperation scripts do **not** load `arms.json` automatically: update their hard-coded settings or CLI arguments separately. The CLI examples below describe the original bench setup.

Calibrate each arm with its motion area clear and the arm supported as needed:

```sh
python calibrate_arm.py leader
python calibrate_arm.py follower
```

Example teleoperation using the recorded macOS ports (replace them and the IDs for your hardware):

```sh
python teleoperate_arms.py \
  --robot.type=so101_follower \
  --robot.port=/dev/cu.usbmodem5A7A0547771 \
  --robot.id=so101_follower_5A7A054777 \
  --teleop.type=so101_leader \
  --teleop.port=/dev/cu.usbmodem5A680086601 \
  --teleop.id=so101_leader_5A68008660 \
  --fps=30 \
  --smooth-tau=0.06 --smooth-deadband=0.2 --smooth-speed=80
```

The launcher smooths position targets with a 60 ms low-pass time constant, a 0.2-unit deadband, and an 80-unit/second command speed limit. Units are LeRobot calibrated position units, not necessarily degrees. It starts targets at the observed follower position and uses the targets accepted by the follower for subsequent updates. After a loop stall, the speed allowance is capped at one 30 Hz frame to avoid a large catch-up step. Smoothing adds some response lag; increase `--smooth-tau` for stronger filtering or reduce it for quicker response. These options take effect when restarting the launcher. They cannot fix mechanical play, power problems, or servo oscillation while holding still.

The launcher retries configuration writes at least three times and supplies `--robot.max_relative_target` defaults of 10 for shoulder pan/lift, elbow flex, and wrist roll, and 20 for wrist flex and gripper. An explicit `--robot.max_relative_target` argument overrides these defaults. These limits do not establish collision safety.

For an instrumented run, use `diagnose_teleop.py` with the same robot/teleop arguments plus `--teleop_time_s=5` and an explicit `--robot.max_relative_target` setting. The diagnostic script waits three seconds before recording; despite its name, the duration comes from the CLI argument. It overwrites `diagnostics/loop.txt`, `diagnostics/teleop_5s.json`, and `diagnostics/teleop_5s.log`.

## VIAFLO pipettor terminal control

The imported Generation 3 controller provides identity/status, aspirate, dispense,
dry cycle, and purge through a terminal prompt. It currently verifies the existing
125 µL single-channel pipette (SN 07064070). On the pipette select **PC Control
(ComM)**, then run from this repository:

```sh
python3 viaflo_control.py build
python3 viaflo_control.py paired
python3 viaflo_control.py shell --address 00-16-a4-4c-9a-ac
```

Use `help` in the prompt. After physically verifying empty, `confirm-empty`
initializes the session's volume tracking; `cycle 5` performs a 5 µL dry test
with the tip out of liquid. `aspirate 10` and `dispense 10` command µL at speed 1.
See [setup, commands, and device limits](tools/viaflo/README.md) before operating.
The native Bluetooth helper builds on macOS; serial support has a separate
`requirements-viaflo.txt`. No host network settings are changed.

## Tool swapper design

The latest [v4 flared pipette design](design/tool_swapper_v4_flared_pipette/README.md)
combines the v2 keyed flared-dowel coupling with a 31 mm pipette collar, compact
round receiver, and 5 mm wrist spacer. Its README identifies the printable pair,
assembly orientation, STEP export limitations, and geometry validation results.

The [fitted v3 pair](design/tool_swapper_v3/README.md) and its
[thin-wall male variant](design/tool_swapper_v3_thin_wall/README.md) remain
available. Use the matching parts specified in each design README; the thin-wall
variant has different screw-head clearance. These are unqualified prototypes,
not interchangeable production releases.

The [second design](design/tool_swapper_v2/README.md) uses an asymmetric vertical key, a single-orientation entry slot, and an internal flared cavity that narrows through a 45° turn. Three headed dowels follow ramps for 0.8 mm nominal draw-in. This version removes the pin lock and retains the original SO-101 wrist mounting pattern. Physical fit and clamp preload require testing.

![Design 2 keyhole coupling](design/tool_swapper_v2/diagrams/design_overview.png)

Download the [v2 CAD, STL, and source package](design/tool_swapper_v2/SO101_tool_swapper_v2.zip), or use its individual files. The original design remains below.

Start with the [detailed design README](design/tool_swapper_v1/README.md) for dimensions, docking sequence, proposed hardware, manufacturing considerations, and rebuild commands. Open `design/tool_swapper_v1/preview.html` in a browser for the included preview, or import the STEP/STL files from `cad/` into your CAD tool or slicer. A packaged copy is included as `SO101_tool_swapper_v1.zip`.

The mechanism uses a quarter-turn interrupted screw, a spring-return locking pin/yoke, and an open-top rack. The receiver includes an unfinished tool blank; a pipette holder or actuator is not implemented.

**Prototype status:** CAD checks cover sampled geometry and interference only. The parts have no verified payload, strength, backlash, or cycle-life rating. Fit-check by hand before powered trials. Robot scripts can move hardware; keep the workspace clear and support the follower when torque is disabled. Removing the gripper motor may require changes to the robot motor configuration.

## Dependencies and licensing

Robot dependencies are listed in `requirements.txt`; CAD dependencies and commands are documented separately in the design README. Local virtual environments, caches, macOS metadata, and credential files are excluded from Git.

The upstream SO-101 reference CAD is attributed in the design README, with its Apache-2.0 license retained at [reference/LICENSE](design/tool_swapper_v1/reference/LICENSE) and provenance in `reference/upstream_commit.json`. No additional license is assigned to the original project files in this initial publication.

## SO-101 robot visualizer

### Position recorder and sequence player

The [Sequence Studio](robot_viewer/README.md) adds browser-based leader/follower
teleoperation, named follower pose capture, autosaved sequence libraries,
drag-to-reorder steps, dwell times, a smooth joint-space planner, Cartesian
pickup-tip actions (3 mm down/up in base Z), a translucent 3D preview with tool
paths, and guarded follower playback. Simulation is available
without connected hardware. The original standalone visualizer remains at
`/model-viewer.html`.

Build the browser with `cd robot_viewer && npm ci && npm run build`, then from the
repository root start `.venv/bin/python -m so101_studio --enable-hardware` and open
**http://127.0.0.1:8766**. Startup stays in simulation; connecting and moving an arm
require explicit browser actions. Omit `--enable-hardware` for simulation only.
The planner bounds joint commands but does not check collisions. See the linked
instructions for calibration, Stop/hold behavior, and the physical setup workflow.

### Original standalone model explorer

The original Robot View includes official follower and leader URDFs, STL meshes, joint sliders, orbit controls, and demo motion. This separate page runs entirely as a visual simulation and does not connect to hardware. With Node.js 22.12+ installed, run from the repository root:

```sh
cd robot_viewer
npm ci
npm run dev -- --port 5173
```

Open http://127.0.0.1:5173/model-viewer.html and keep the terminal running. Drag to orbit, right-drag to pan, scroll to zoom, and use the sliders to move joints. See the [viewer instructions](robot_viewer/README.md) for model files, display options, production builds, and calibration notes.

## Development and verification

See the [backend development guide](so101_studio/README.md) for module ownership,
server options, and local data handling. After installing the browser dependencies,
run the complete hardware-free regression suite and production build:

```sh
.venv/bin/python -m unittest discover -s tests -v
cd robot_viewer
npm run build
```

The tests use simulated devices and fake transports; they do not commission real
hardware. CAD validation reports document separate geometry checks and are not
regenerated by this test suite. Rebuild commands and dependencies live in each
CAD variant's README.

Generated browser bundles, installed dependencies, virtual environments, local
sequence libraries, credentials, and VIAFLO packet logs remain ignored by Git.
Export important sequences from Studio or back up `data/sequences.json` separately.
