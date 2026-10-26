# SO-101 Sequence Studio

A local browser interface for teaching named follower positions with the leader,
arranging sequences, planning smooth joint trajectories, previewing them in 3D,
and playing the stored plan on the follower. The layout and ghost/path preview
follow the workflow of the local neilsim viewer. The original model explorer is
retained at `/model-viewer.html`.

## Start

From the repository root, build the browser once (Node.js 22.12+):

```sh
cd robot_viewer
npm ci
npm run build
cd ..
```

Start in simulation, without opening any robot serial ports:

```sh
.venv/bin/python -m so101_studio
```

Open **http://127.0.0.1:8766**. Simulation needs only Python's standard library.
If the local Node command is too old, build with
`/opt/homebrew/bin/node node_modules/vite/bin/vite.js build` from `robot_viewer/`.

To make physical connection available in the browser, use the existing LeRobot
virtual environment (`requirements.txt`) and start instead with:

```sh
.venv/bin/python -m so101_studio --enable-hardware
```

This flag only permits connection. Startup remains in simulation and does not
open or command either arm. Leave the server running while using the browser.
Use Ctrl+C to stop it. The server binds only to `127.0.0.1`; it does not change
Wi-Fi, routes, DNS, or any host network configuration.

## Teach, arrange, and play

1. **Connect:** choose **Physical follower**, optionally include the leader, and
   click **Connect arms**. For playback alone, uncheck the leader option. Both
   adapters are selected by their exact USB serial numbers in `arms.json`, even
   if their macOS device paths have changed. Stop any existing
   `teleoperate_arms.py` or other serial controller before connecting.
   The connection panel lists each configured adapter as missing, detected and
   ready, or detected but busy. **Refresh USB detection** only enumerates devices
   and inspects OS port ownership; it does not open the buses. The app refuses
   to open either arm if another controller is already using either required port.
2. **Teleoperate:** with the motion area clear, click **Start teleoperation**.
   The follower is seeded with its measured position before torque is enabled;
   the leader is released. Studio uses the same `TargetFilter` as
   `teleoperate_arms.py --fps=60 --smooth-tau=0.06 --smooth-deadband=0.2 --smooth-speed=80`:
   a **60 Hz target**, 60 ms low-pass smoothing, 0.2-unit deadband, and an
   80-unit/s slew limit. The installed LeRobot defaults and Studio use degrees
   for arm joints and percent for the gripper. Targets start from follower
   feedback, and the filter restarts fresh whenever teleoperation starts.
   This replaces Studio's previous 25-unit/s acceleration-ramped filter.
   Like the CLI launcher, teleoperation limits each goal's lead over fresh
   follower feedback to **10°** for shoulder pan/lift, elbow flex and wrist roll,
   **20°** for wrist flex, and **20 percentage points** for the gripper. The
   accepted, clipped goal is fed back into the filter so it cannot accumulate
   a distant target while the follower catches up. The status reports when
   this limiting is active. Normal teleoperation lag does not trigger the
   separate sequence-playback tracking cutoff.
3. **Record:** type a name and click **Record position**, or press **R** while
   focus is outside a form control. Every click records a fresh **measured
   follower** position, including the gripper, and saves it to disk. Recording
   works during teleoperation or while idle. It captures individual key poses,
   not a continuous video or trajectory recording.
4. **Arrange:** rename positions inline, drag rows or use their up/down arrows,
   duplicate a position, remove it, and set its hold time (0–30 seconds). Clicking
   a row displays a translucent preview of that saved pose without commanding
   hardware. The library supports multiple named sequences and JSON import/export.
   **＋ Pickup tip** appends a relative action: move the tool **3 mm down along
   base Z**, then **3 mm up** to the same pose. Put it immediately after your
   recorded approach position; it follows that position when reordered. If it
   is the first step, it starts from the current pose used for planning. You can
   rename, duplicate, reorder, remove, export and import it like a recorded step.
   Adding the action does not move the arm.
5. **Stop teaching:** click **Stop** or press **Escape**. The follower holds its
   measured position. Planning and execution require teleoperation to be stopped.
6. **Plan:** choose speed and acceleration, then click **Plan sequence**. The
   planner includes the move from the follower's current position to the first
   saved position, followed by every step in order. It synchronizes all six
   joints with quintic easing, zero velocity/acceleration at each position, and
   the requested dwell. The visualizer shows the gripper-frame path and waypoint
   markers. Recorded positions use joint-space curves. Pickup actions use
   Cartesian inverse kinematics to hold tool X/Y, orientation and gripper
   opening fixed during both vertical legs, stopping at the bottom and top.
   An unreachable path or joint-limit violation rejects the plan and names the
   action; teach an approach position with more travel available in that case.
7. **Preview (optional):** click **Preview** to animate the translucent arm over the live
   follower. Pause or scrub the timeline to inspect it. Execution is available
   immediately after planning; preview is optional. Preview does
   not move hardware. The actual follower remains visible and keeps updating.
8. **Execute:** explicitly click the execute button. The backend uses the same
   stored plan used for preview. It checks the current start pose, calibration,
   sequence revision, and motion state before commanding the follower. Any edit
   or move of more than one degree / gripper percentage point from the planned
   start requires a new plan. Replan before running again.

In **Simulation**, use the six joint sliders instead of a leader. They affect
only the virtual arm. Record and plan synchronize that virtual pose to the
backend. Simulation loads the configured follower's calibration file when
available, without opening a serial port, so recorded hardware poses can be
planned and played virtually even if they extend beyond nominal model limits.
The pose panel identifies the limits in use; absent a valid calibration file,
it falls back to the model limits. Mixed hardware/simulation sequences can be
previewed, but positions labeled **SIM** cannot be executed on real hardware.
For follower playback, re-record simulated steps on the arm or remove them;
every recorded position must match the follower and its current calibration.
Relative pickup actions are resolved using that plan's start pose and limits;
they do not contain simulated recorded positions.

## Pickup distance and reference frame

The pickup action uses the same URDF `gripper_frame_link` as the visualizer;
Z is the robot base's vertical axis, **not the tilted tool's local Z**. Both legs
keep the modeled tool orientation fixed, so a rigid attachment also translates
vertically. The existing model and calibration must match the real arm for the
physical direction and distance to agree. Servo resolution, backlash, tracking
and calibration mean that a commanded 3 mm move is **not a guarantee of measured
3 mm physical travel**. This is a position move, without force/contact sensing.

The planner solves IK at 0.1 mm spacing, joins the joint solutions with smooth
cubic Hermite curves and applies quintic time scaling. Interpolated tool poses
are checked against the vertical line to a 0.001 mm model tolerance, including
intermediate points. Joint travel extrema and speed/acceleration bounds are
checked analytically over each polynomial. Each leg lasts at least one second,
and longer when needed to respect the selected joint speed and acceleration.
The browser and executor evaluate the same stored curve, including the exact
return to the preceding joint pose. Pickup actions can also execute directly
after planning, with preview optional.

## Motion behavior and limits

- Arm values are **LeRobot calibrated degrees**; gripper values are **0–100%**.
  This is explicit throughout documents, the driver, and the planner. Speed and
  acceleration settings apply numerically in each joint's own units.
- Hardware body limits come from the connected follower's calibrated travel;
  simulation uses its saved calibration when available, otherwise the nominal
  URDF limits. Small assembly/calibration differences
  can put a legitimate hardware pose beyond the model's nominal limit. Those
  poses are displayed and recorded accurately, while every hardware plan and
  command is still checked against that follower's calibration. Gripper limits
  are 0–100%.
- **No collision checking or obstacle avoidance is implemented.** The planner
  bounds commanded joint speed/acceleration, but does not validate self-collision,
  table clearance, payload, actuator forces, or attachments. Inspect the complete
  swept path and keep the actual workspace clear before physical execution.
- The visual model uses the upstream new-calibration convention. Its zero angles
  can differ from the physical calibration midpoint. The displayed gripper
  opening is illustrative (0–100° mapped from 0–100%); it is not calibrated jaw
  spacing. The preview is not a collision-accurate digital twin.
- One serialized control loop targets **60 Hz** for teleoperation and sequence
  playback. Actual frequency depends on serial I/O and host scheduling. Both
  use elapsed time capped at one 30 Hz frame after a delay; delays over 250 ms
  fault. The CLI filter has the same 30 Hz catch-up cap (and initial time step).
  Recorded playback evaluates the reviewed trajectory directly, using the
  sequence's selected speed/acceleration. Applying the teleoperation filter
  there would distort the planned path, including Cartesian pickup strokes.
- Studio owns the serial connections while connected. It reuses the CLI's
  filter in-process so recording, Stop, feedback checks and browser heartbeat
  remain integrated. Do not run the CLI concurrently against the same ports.
- A loop delay over 250 ms, communication failure, or excessive following error
  (8° for arm joints, 12 percentage points for the gripper) stops playback and
  faults the session. Final completion requires measured arrival within 1.5
  units, with a 3-second settling allowance. Reconnect after a fault.
- Only the controlling tab renews the 3-second motion lease. Closing it or losing
  its heartbeat stops motion. A separate tab cannot keep that motion alive.
- **Stop is a software hold, not a physical emergency stop.** A communication
  failure can prevent a hold command from reaching the motors. Keep physical
  power control accessible. On a confirmed Stop, the follower remains powered
  and holding. Server shutdown and Disconnect preserve torque to avoid dropping
  the arm. Support the arm and use **Release torque…** when you want to unpower it.
- Connecting performs the bus handshake and calibration/position reads only.
  It does not invoke automatic calibration or rewrite PID, limits, homing,
  acceleration registers, or operating mode. The motors must already be
  calibrated and configured in position mode by the existing setup. Calibration
  mismatch or incomplete files produce an error instead of an interactive prompt.

## Saved data

Sequences autosave atomically to `data/sequences.json` (ignored by Git). Keep a
backup or export important sequences. Positions include their source mode and a
hash of the follower USB identity/calibration to prevent accidental playback on
another setup. Imports are validated for units, names, joint limits, unique
position IDs, dwell values, and a 200-position limit. Plans are limited to
10 minutes. Concurrent edits from an older tab are rejected; refresh that page.

Use `--data /absolute/path/sequences.json` for a separate library and
`--arms /absolute/path/arms.json` for another explicitly identified pair. The
`id` fields in the arm configuration must match the existing calibration files
under LeRobot's calibration directory (`robots/so_follower/` and
`teleoperators/so_leader/`). The recorded `port` fields are reference information;
connection requires an exact `usb_serial` match.

## Development and checks

For live browser edits, run the Python API and Vite in separate terminals:

```sh
# Repository root
.venv/bin/python -m so101_studio --dev-origin http://127.0.0.1:5173

# A second terminal
cd robot_viewer
npm run dev
```

Open `http://127.0.0.1:5173`. Vite forwards `/api` to port 8766. Its port is fixed
at 5173 to keep the allowed control origin explicit. A production build can be
served directly by Python; `npm run preview` alone serves only the static UI and
cannot control the robot. The API requires a per-server token for mutations,
rejects foreign origins, and validates the loopback Host header.

Run automated checks from the root:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_so101_studio.py' -v
cd robot_viewer
npm run build
```

Tests exercise analytic bounds, exact browser/server trajectory agreement,
measured pose capture, persistence/revision conflicts, plan invalidation,
control ownership, watchdog/stop/fault handling, API guards, and the hardware
adapter with fake buses. They never open a real serial port. Physical motion
must still be commissioned and checked on the actual bench.

## Original model explorer

Open `/model-viewer.html` for the original standalone leader/follower model
viewer with joint sliders, orbit controls, wireframe, joint frames, demo motion,
and URDF download. It has no hardware control. It also works with Vite alone.

The official URDFs, meshes and provenance are in `public/robots/so101/`.
Source: https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation/SO101
The pinned upstream revision is recorded in `provenance.json`, and Apache-2.0
licensing is retained in `LICENSE`. The model files remain unmodified.
