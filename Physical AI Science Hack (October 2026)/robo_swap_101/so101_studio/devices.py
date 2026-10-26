"""Hardware is opened only on a browser connection request with --enable-hardware.

Monitoring does not call LeRobot's configure/connect wrappers, which enable torque
and rewrite motor settings. Only the serial bus handshake and reads run on connect.
"""
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from .model import HOME, JOINTS, LIMITS, pose


def calibrated_limits(raw):
    """Convert the recorded STS3215 calibration to degrees without opening a bus."""
    if not isinstance(raw, dict) or set(raw) != set(JOINTS):
        raise ValueError("Calibration must contain all six joints")
    limits = {}
    for i, joint in enumerate(JOINTS, 1):
        entry = raw[joint]
        lo, hi = entry["range_min"], entry["range_max"]
        if entry["id"] != i or type(lo) is not int or type(hi) is not int or not 0 <= lo < hi <= 4095:
            raise ValueError(f"Invalid calibration for {joint}")
        half_range = (hi - lo) * 180 / 4095
        limits[joint] = (-half_range, half_range) if joint != "gripper" else (0.0, 100.0)
    return limits


class Simulation:
    mode = "simulation"
    calibration = None
    limits = LIMITS
    has_leader = False

    def __init__(self, config=None):
        self.limits = dict(LIMITS)
        self.limits_source = "Nominal model limits"
        if config and config.get("follower"):
            try:
                from lerobot.utils.constants import HF_LEROBOT_CALIBRATION
                path = HF_LEROBOT_CALIBRATION / "robots/so_follower" / f"{config['follower']['id']}.json"
                self.limits = calibrated_limits(json.loads(path.read_text()))
                self.limits_source = "Follower calibration (offline)"
            except (ImportError, OSError, ValueError, KeyError, TypeError):
                self.limits_source = "Nominal model limits (follower calibration unavailable)"
        self.position = HOME.copy()
        self.armed = False

    def read(self):
        return self.position.copy()

    def enable(self, leader=False):
        self.armed = True

    def send(self, target):
        self.position = pose(target, self.limits)

    def release(self):
        self.armed = False

    def close(self):
        pass


def available_ports():
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    return [{"port": p.device, "usb_serial": p.serial_number, "description": p.description}
            for p in list_ports.comports() if p.serial_number]


def port_users(port):
    """Inspect OS file handles without opening the serial bus or sending packets."""
    lsof = shutil.which("lsof")
    if not lsof:
        raise ValueError("Cannot check serial-port ownership: lsof is not installed")
    paths = [port]
    if port.startswith("/dev/cu."):
        alias = port.replace("/dev/cu.", "/dev/tty.", 1)
        if Path(alias).exists():
            paths.append(alias)
    result = subprocess.run([lsof, "-nP", "-Fpc", *paths], capture_output=True, text=True, timeout=3)
    if result.returncode not in (0, 1) or (result.returncode == 1 and result.stderr.strip()):
        raise ValueError(f"Could not check ownership of {port}: {result.stderr.strip()}")
    users = []
    for line in result.stdout.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            users.append({"pid": int(line[1:]), "process": "controller"})
        elif line.startswith("c") and users:
            users[-1]["process"] = line[1:]
    return users


def device_inventory(config):
    ports = available_ports()
    arms = {}
    for role, identity in config.items():
        matches = [p for p in ports if p["usb_serial"] == identity["usb_serial"]]
        users = port_users(matches[0]["port"]) if len(matches) == 1 else []
        arms[role] = {**identity, "port": matches[0]["port"] if len(matches) == 1 else None,
                      "detected": len(matches) == 1, "users": users,
                      "busy": any(user["pid"] != os.getpid() for user in users)}
    return {"ports": ports, "arms": arms}


class Hardware:
    mode = "hardware"
    limits_source = "Connected follower calibration"

    def __init__(self, config, include_leader=True):
        from lerobot.motors import Motor, MotorCalibration, MotorNormMode
        from lerobot.motors.feetech import FeetechMotorsBus
        from lerobot.utils.constants import HF_LEROBOT_CALIBRATION

        self.buses = {}
        self.armed = False
        self.has_leader = include_leader
        self.limits = dict(LIMITS)
        ports = available_ports()
        roles = ("follower", "leader") if include_leader else ("follower",)
        if include_leader and config["leader"]["usb_serial"] == config["follower"]["usb_serial"]:
            raise ValueError("Leader and follower must have different USB serial numbers")
        # Check the entire pair before opening either bus. Exclusive serial locks
        # alone do not detect an already-running non-exclusive LeRobot process.
        selected = {}
        for role in roles:
            identity = config[role]
            matches = [p for p in ports if p["usb_serial"] == identity["usb_serial"]]
            if len(matches) != 1:
                detected = ", ".join(p["usb_serial"] for p in ports) or "none"
                raise ValueError(f"Connect the {role} USB adapter with serial {identity['usb_serial']}; "
                                 f"found {len(matches)} matches. Detected USB serials: {detected}. "
                                 "Check the role assignments in arms.json.")
            users = port_users(matches[0]["port"])
            if users:
                owners = ", ".join(f"{user['process']} (PID {user['pid']})" for user in users)
                raise ValueError(f"{role.title()} {identity['usb_serial']} is detected but busy in {owners}. "
                                 "Stop the separate teleoperation/controller before connecting in Studio.")
            selected[role] = matches[0]["port"]
        try:
            for role in roles:
                identity = config[role]
                folder = "robots" if role == "follower" else "teleoperators"
                calibration_file = HF_LEROBOT_CALIBRATION / folder / f"so_{role}" / f"{identity['id']}.json"
                if not calibration_file.is_file():
                    raise ValueError(f"Missing {role} calibration: {calibration_file}. Calibrate separately first.")
                raw = json.loads(calibration_file.read_text())
                if set(raw) != set(JOINTS):
                    raise ValueError(f"Incomplete {role} calibration; all six joints are required")
                calibration = {j: MotorCalibration(**raw[j]) for j in JOINTS}
                for i, j in enumerate(JOINTS, 1):
                    c = calibration[j]
                    if c.id != i or not 0 <= c.range_min < c.range_max <= 4095:
                        raise ValueError(f"Invalid {role} calibration for {j}")
                motors = {j: Motor(i, "sts3215", MotorNormMode.RANGE_0_100 if j == "gripper" else MotorNormMode.DEGREES)
                          for i, j in enumerate(JOINTS, 1)}
                bus = FeetechMotorsBus(port=selected[role], motors=motors, calibration=calibration)
                self.buses[role] = bus
                bus.connect()
                # Also lock against other controllers that honor exclusive mode.
                bus.port_handler.ser.exclusive = True
                if not bus.is_calibrated:
                    raise ValueError(f"{role.title()} motor calibration does not match its file. Calibrate separately first.")
                if role == "follower":
                    self.limits = calibrated_limits(raw)
                    signature = {"usb_serial": identity["usb_serial"], "calibration": {j: asdict(c) for j, c in calibration.items()}}
                    self.calibration = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
            self.read()
        except Exception:
            self.close()
            raise

    def read(self):
        return pose(self.buses["follower"].sync_read("Present_Position", num_retry=2), self.limits)

    def leader(self):
        return self.buses["leader"].sync_read("Present_Position", num_retry=2)

    def enable(self, leader=False):
        bus = self.buses["follower"]
        modes = bus.sync_read("Operating_Mode", normalize=False, num_retry=2)
        if any(v != 0 for v in modes.values()):
            raise ValueError("Follower motors must already be configured in position mode. Use the calibration/teleop setup first.")
        if leader:
            if not self.has_leader:
                raise ValueError("Reconnect with the leader enabled to teleoperate")
            self.buses["leader"].disable_torque(num_retry=3)
        # Seed the goal from measured position BEFORE enabling torque: never jump to a stale goal.
        self.send(self.read())
        bus.enable_torque(num_retry=3)
        self.armed = True

    def send(self, target):
        self.buses["follower"].sync_write("Goal_Position", pose(target, self.limits), num_retry=2)

    def release(self):
        self.buses["follower"].disable_torque(num_retry=3)
        self.armed = False

    def close(self):
        # Deliberately preserve torque. A disconnect must not drop an unsupported arm.
        for bus in self.buses.values():
            if bus.is_connected:
                bus.disconnect(disable_torque=False)
