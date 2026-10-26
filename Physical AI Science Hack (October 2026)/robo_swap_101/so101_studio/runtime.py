"""Serialized robot access, motion ownership, feedback checks and browser watchdog."""
import math
import threading
import time
import uuid

from .devices import Hardware, Simulation
from .filtering import TELEOP_RELATIVE_LIMITS, TargetFilter, limit_relative_target
from .model import JOINTS, name, pose
from .planner import Plan

CONTROL_FPS = 60
PERIOD = 1 / CONTROL_FPS
MAX_TIMESTEP = 1 / 30
TELEOP_SETTINGS = {"tau": 0.06, "deadband": 0.2, "speed": 80.0}
LEASE_SECONDS = 3.0
START_TOLERANCE = 1.0


class Runtime:
    def __init__(self, store, config, enable_hardware=False, clock=time.monotonic, hardware_factory=Hardware):
        self.store, self.config = store, config
        self.enable_hardware = enable_hardware
        self.hardware_factory, self.clock = hardware_factory, clock
        self.lock = threading.RLock()
        self.device = Simulation(config)
        self.observed = self.device.read()
        self.observed_at = clock()
        self.mode = "simulation"
        self.activity = "idle"
        self.message = "Simulation ready. Set a pose and record your first position."
        self.error = None
        self.owner = None
        self.heartbeat_at = 0
        self.plan = None
        self.plan_sequence = None
        self.reviewed = False
        self.elapsed = 0
        self.step = 0
        self.last_tick = clock()
        self.last_command = self.observed.copy()
        self.teleop_filter = None
        self.teleop_limited_joints = []
        self.shutdown = threading.Event()
        self.thread = None
        self.stop_generation = 0

    def start(self):
        self.thread = threading.Thread(target=self._loop, name="so101-control", daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.shutdown.is_set():
            with self.lock:
                # Connection/startup holds this lock while doing serial I/O,
                # then _claim resets last_tick. A timestamp captured BEFORE
                # waiting could predate that reset and falsely trip dt < 0.
                began = self.clock()
                try:
                    self.tick(began)
                except Exception as exc:
                    self._fault(str(exc))
            self.shutdown.wait(max(0, PERIOD - (self.clock() - began)))

    def _read(self):
        self.observed = pose(self.device.read(), self.device.limits)
        self.observed_at = self.clock()
        return self.observed.copy()

    def _idle(self):
        if self.activity != "idle":
            raise ValueError("Stop motion before this action" if self.activity != "fault" else "Reconnect to clear the robot fault")

    def _invalidate(self):
        self.plan = None
        self.plan_sequence = None
        self.reviewed = False

    def _claim(self, client):
        self.owner = name(client, "Browser session")
        self.heartbeat_at = self.clock()
        self.last_tick = self.clock()

    def heartbeat(self, client):
        with self.lock:
            if self.owner == client:
                self.heartbeat_at = self.clock()

    def state(self):
        with self.lock:
            return {"mode": self.mode, "activity": self.activity, "pose": self.observed.copy(),
                    "age": max(0, self.clock() - self.observed_at), "message": self.message, "error": self.error,
                    "armed": self.device.armed, "has_leader": self.device.has_leader,
                    "limits": self.device.limits, "hardware_enabled": self.enable_hardware,
                    "limits_source": getattr(self.device, "limits_source", "Device limits"),
                    "control_fps": CONTROL_FPS, "teleop_settings": TELEOP_SETTINGS.copy(),
                    "teleop_relative_limits": TELEOP_RELATIVE_LIMITS.copy(),
                    "teleop_limited_joints": self.teleop_limited_joints.copy() if self.activity == "teleop" else [],
                    "owner": self.owner, "plan_id": self.plan.id if self.plan else None,
                    "reviewed": self.reviewed, "elapsed": self.elapsed, "step": self.step,
                    "duration": self.plan.duration if self.plan else 0}

    def connect(self, mode, include_leader=True):
        with self.lock:
            if self.activity in ("teleop", "executing"):
                raise ValueError("Stop motion before changing connections")
            if mode not in ("simulation", "hardware"):
                raise ValueError("Unknown connection mode")
            if mode == "hardware" and not self.enable_hardware:
                raise ValueError("Restart the server with --enable-hardware to connect the arms")
            if mode == "hardware" and self.mode == "hardware":
                raise ValueError("Disconnect the current arms before reconnecting")
            replacement = (self.hardware_factory(self.config, include_leader)
                           if mode == "hardware" else Simulation(self.config))
            self.device.close()
            self.device = replacement
            self.mode = mode
            self._read()
            self.activity, self.error, self.owner = "idle", None, None
            self._invalidate()
            self.last_tick = self.clock()
            self.message = ("Arms connected for monitoring. Start teleoperation to move the follower."
                            if mode == "hardware" else "Simulation ready. Hardware disconnected; existing torque is preserved.")

    def set_simulation(self, value):
        with self.lock:
            self._idle()
            if self.mode != "simulation":
                raise ValueError("Joint sliders are only available in simulation")
            self.device.send(pose(value, self.device.limits))
            self._read()
            self._invalidate()

    def save_sequence(self, key, value, revision):
        with self.lock:
            if self.activity == "executing":
                raise ValueError("Stop playback before editing a sequence")
            saved = self.store.update(key, value, revision)
            self._invalidate()
            return saved

    def record(self, key, revision, label):
        with self.lock:
            if self.activity not in ("idle", "teleop"):
                raise ValueError("Positions can be recorded while idle or teleoperating")
            doc = self.store.get(key)
            if doc["revision"] != revision:
                raise ValueError("This sequence changed in another tab. Refresh before recording.")
            point = {"id": str(uuid.uuid4()), "name": name(label), "pose": self._read(), "dwell": 0.5,
                     "source": self.mode, "calibration": self.device.calibration}
            doc["points"].append(point)
            saved = self.store.update(key, doc, revision)
            self._invalidate()
            self.message = f"Recorded {point['name']} from the {'follower' if self.mode == 'hardware' else 'simulated arm'}."
            return saved

    def make_plan(self, key, revision, speed, acceleration):
        with self.lock:
            self._idle()
            self._invalidate()
            doc = self.store.get(key)
            if doc["revision"] != revision:
                raise ValueError("The sequence changed. Refresh before planning.")
            if self.mode == "hardware":
                recorded = [p for p in doc["points"] if p.get("kind", "pose") == "pose"]
                simulated = [p["name"] for p in recorded if p["source"] != "hardware"]
                if simulated:
                    raise ValueError("Hardware playback requires positions recorded with this follower and its current calibration. "
                                     f"Simulated positions: {', '.join(simulated)}. Re-record these from the follower or remove them; "
                                     "Simulation can preview the mixed sequence.")
                incompatible = [p["name"] for p in recorded if p["calibration"] != self.device.calibration]
                if incompatible:
                    raise ValueError("These positions do not match the follower's current calibration: "
                                     f"{', '.join(incompatible)}. Re-record them with this follower.")
            self.plan = Plan(self._read(), doc["points"], speed, acceleration, self.device.limits)
            self.plan_sequence = (key, revision)
            self.reviewed = False
            self.elapsed, self.step = 0, 0
            self.message = "Plan ready. Execute or optionally preview the motion."
            return self.plan.public()

    def review(self, plan_id):
        with self.lock:
            self._idle()
            self._check_plan(plan_id)
            self.reviewed = True
            self.message = "Preview complete. Sequence is ready to execute."

    def _check_plan(self, plan_id):
        if not self.plan or self.plan.id != plan_id:
            raise ValueError("Plan is no longer current. Plan again.")
        key, revision = self.plan_sequence
        if self.store.get(key)["revision"] != revision:
            self._invalidate()
            raise ValueError("Sequence changed. Plan again.")

    def execute(self, plan_id, client):
        generation = self.stop_generation
        with self.lock:
            if generation != self.stop_generation:
                raise ValueError("Start cancelled by Stop")
            self._idle()
            self._check_plan(plan_id)
            current = self._read()
            if max(abs(current[j] - self.plan.start[j]) for j in JOINTS) > START_TOLERANCE:
                self._invalidate()
                raise ValueError("Follower moved from the planned start. Plan again.")
            # Validate the client before writes, and enable only at the explicit Execute action.
            name(client, "Browser session")
            try:
                self.device.enable()
                if generation != self.stop_generation:
                    self._hold()
                    raise ValueError("Start cancelled by Stop")
                current = self._read()
                if max(abs(current[j] - self.plan.start[j]) for j in JOINTS) > START_TOLERANCE:
                    raise ValueError("Follower moved while enabling torque. Reconnect, plan again.")
            except Exception as exc:
                self._fault(str(exc))
                raise
            self._claim(client)
            self.activity = "executing"
            self.last_command = current
            self.elapsed, self.step = 0, 0
            self.message = "Executing planned sequence."

    def teleoperate(self, client):
        generation = self.stop_generation
        with self.lock:
            if generation != self.stop_generation:
                raise ValueError("Start cancelled by Stop")
            self._idle()
            if self.mode != "hardware" or not self.device.has_leader:
                raise ValueError("Connect both the leader and follower to teleoperate")
            name(client, "Browser session")
            try:
                self.device.enable(leader=True)
                self.last_command = self._read()
                if generation != self.stop_generation:
                    self._hold()
                    raise ValueError("Start cancelled by Stop")
            except Exception as exc:
                self._fault(str(exc))
                raise
            self.teleop_filter = TargetFilter(**TELEOP_SETTINGS)
            self.teleop_limited_joints = []
            self._claim(client)
            self._invalidate()
            self.activity = "teleop"
            self.message = "Teleoperation active · 60 Hz target · CLI smoothing profile. Move the leader and click Record position."

    def _hold(self):
        if self.device.armed:
            self.device.send(self._read())

    def stop(self, message="Stopped. Follower holds its measured position."):
        # Set this before waiting on serial I/O so an in-flight enable cannot start motion afterward.
        self.stop_generation += 1
        with self.lock:
            was_fault = self.activity == "fault"
            was_active = self.activity in ("executing", "teleop")
            self.owner = None
            self.activity = "fault" if was_fault else "idle"
            self._invalidate()
            if was_active:
                try:
                    self._hold()
                except Exception as exc:
                    self.error = f"Stop requested; could not confirm a hold: {exc}. Use the physical power control if needed."
                    self.activity = "fault"
            self.message = self.error if self.activity == "fault" else message

    def _fault(self, error):
        # Attempt a measured hold once. Never replay an old position after a communication fault.
        was_active = self.activity in ("teleop", "executing")
        self.activity, self.owner = "fault", None
        self._invalidate()
        if was_active:
            try:
                self._hold()
            except Exception:
                error += "; hold could not be confirmed — use the physical power control if needed"
        self.error = error
        self.message = f"Motion stopped: {error}"

    def release(self):
        with self.lock:
            self.stop()
            self.device.release()
            self.message = "Follower torque released. Support the arm."

    def tick(self, now):
        """One serialized control iteration; also exercised directly by deterministic tests."""
        generation = self.stop_generation
        dt = now - self.last_tick
        self.last_tick = now
        if self.activity == "fault":
            return
        self._read()
        if generation != self.stop_generation:
            return
        if self.activity not in ("executing", "teleop"):
            return
        if now - self.heartbeat_at > LEASE_SECONDS:
            self.stop("Browser heartbeat lost. Motion stopped; follower holds position.")
            return
        if dt > 0.25 or dt < 0:
            raise ValueError(f"Control loop stalled (interval {dt * 1000:.1f} ms). Reconnect before restarting motion; replan for sequence playback.")
        # Use elapsed time at the 60 Hz target rate. Cap larger delays at one
        # 30 Hz frame, matching the CLI filter without slowing every 60 Hz tick
        # for normal scheduling jitter. Longer delays never cause catch-up jumps.
        dt = min(dt, MAX_TIMESTEP)
        if self.activity == "teleop":
            leader = self.device.leader()
            action = {}
            for j in JOINTS:
                raw = leader[j]
                if not isinstance(raw, (int, float)) or not math.isfinite(raw):
                    raise ValueError(f"Invalid leader position for {j}")
                lo, hi = self.device.limits[j]
                action[f"{j}.pos"] = min(hi, max(lo, raw))
            observation = {f"{j}.pos": value for j, value in self.observed.items()}
            filtered = self.teleop_filter.apply(action, observation, now)
            requested = pose({j: filtered[f"{j}.pos"] for j in JOINTS}, self.device.limits)
            # The CLI reads fresh follower feedback in send_action, clips the
            # requested lead and feeds the accepted target back into the filter.
            # Normal servo lag must not trip the recorded-path tracking check.
            current = self._read()
            if generation != self.stop_generation:
                return
            target = pose(limit_relative_target(requested, current), self.device.limits)
            self.teleop_limited_joints = [j for j in JOINTS if abs(target[j] - requested[j]) > 1e-4]
            self.message = ("Teleoperation active · follower catching up: " +
                            ", ".join(j.replace('_', ' ') for j in self.teleop_limited_joints) + "."
                            if self.teleop_limited_joints else
                            "Teleoperation active · 60 Hz target · CLI smoothing profile. Move the leader and click Record position.")
        else:
            self.elapsed += dt
            target, segment_index = self.plan.at(self.elapsed)
            self.step = self.plan.segments[segment_index]["step_index"]
            # A planned sequence must follow its planned trajectory rather
            # than changing the path to accommodate lag. Keep its strict check.
            for j in JOINTS:
                tolerance = 12 if j == "gripper" else 8
                if abs(target[j] - self.observed[j]) > tolerance:
                    raise ValueError(f"{j.replace('_', ' ')} is not following the commanded path "
                                     f"(target {target[j]:.2f}, measured {self.observed[j]:.2f}, limit {tolerance})")
        self.device.send(target)
        if self.activity == "teleop":
            # Feed back only targets successfully handed to the driver, just
            # as the CLI feeds robot.send_action's result to this same filter.
            self.teleop_filter.accept({f"{j}.pos": value for j, value in target.items()})
        self.last_command = target
        if self.activity == "executing" and self.elapsed >= self.plan.duration:
            if max(abs(target[j] - self.observed[j]) for j in JOINTS) <= 1.5:
                self.activity, self.owner = "idle", None
                self.reviewed = False
                self.message = "Sequence complete. Follower holds the final position. Replan to run again."
                self._invalidate()
            elif self.elapsed > self.plan.duration + 3:
                raise ValueError("Follower did not settle at the final position")

    def close(self):
        self.shutdown.set()
        if self.thread:
            self.thread.join(timeout=5)
        with self.lock:
            self.stop("Server stopped. Follower torque is preserved.")
            self.device.close()
