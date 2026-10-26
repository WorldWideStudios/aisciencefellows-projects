"""Validated, versioned sequence documents. Joint positions use degrees / gripper %."""
import json
import math
import os
import tempfile
import threading
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
UNITS = "degrees_gripper_percent"
URDF = ROOT / "robot_viewer/public/robots/so101/so101_new_calib.urdf"
LIMITS = {
    joint.attrib["name"]: tuple(math.degrees(float(joint.find("limit").attrib[k])) for k in ("lower", "upper"))
    for joint in ET.parse(URDF).getroot().findall("joint") if joint.attrib["name"] in JOINTS
}
LIMITS["gripper"] = (0.0, 100.0)
# Maximum representation range for calibrated STS3215 degrees. Hardware plans
# and commands are checked against the connected arm's narrower calibration.
HARDWARE_LIMITS = {j: (-180.0, 180.0) for j in JOINTS}
HARDWARE_LIMITS["gripper"] = (0.0, 100.0)
HOME = dict.fromkeys(JOINTS, 0.0)
HOME["gripper"] = 35.0


def number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if not low <= value <= high:
        raise ValueError(f"{label} must be between {low:g} and {high:g}")
    return float(value)


def name(value, label="Name"):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
        raise ValueError(f"{label} must contain 1–80 characters")
    return value.strip()


def pose(value, limits=None):
    if not isinstance(value, dict) or set(value) != set(JOINTS):
        raise ValueError("A position must contain exactly the six SO-101 joints")
    return {j: number(value[j], j, *(limits or LIMITS)[j]) for j in JOINTS}


def document(value):
    if not isinstance(value, dict) or value.get("version") != 1 or value.get("units") != UNITS:
        raise ValueError("Expected a version 1 SO-101 sequence in degrees / gripper percent")
    points = value.get("points")
    if not isinstance(points, list) or len(points) > 200:
        raise ValueError("A sequence can contain at most 200 steps")
    result = {"version": 1, "units": UNITS, "name": name(value.get("name")), "points": []}
    ids = set()
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("Invalid position")
        point_id = name(point.get("id"), "Position ID")
        if point_id in ids:
            raise ValueError("Position IDs must be unique")
        ids.add(point_id)
        kind = point.get("kind", "pose")
        if kind == "pickup_tip":
            # A relative recipe, resolved at planning from the preceding pose.
            # The travel is fixed by the planner: 3 mm down, then 3 mm up.
            result["points"].append({"id": point_id, "name": name(point.get("name")), "kind": kind})
            continue
        if kind != "pose":
            raise ValueError("Unknown sequence step kind")
        source = point.get("source")
        if source not in ("simulation", "hardware"):
            raise ValueError("Position source must be simulation or hardware")
        calibration = point.get("calibration")
        if calibration is not None and (not isinstance(calibration, str) or len(calibration) > 128):
            raise ValueError("Invalid calibration identity")
        result["points"].append({
            "id": point_id, "name": name(point.get("name")),
            # Documents validate the degree representation. The active device's
            # calibration/model limits are enforced at capture, planning and send.
            "pose": pose(point.get("pose"), HARDWARE_LIMITS),
            "dwell": number(point.get("dwell", 0.5), "Dwell", 0, 30),
            "source": source, "calibration": calibration,
        })
    return result


class Store:
    """Atomic disk persistence and optimistic revisions prevent multi-tab lost updates."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.items = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            for key, item in raw.items():
                self.items[key] = {**document(item), "id": key, "revision": int(item["revision"])}
        else:
            self.create({"version": 1, "units": UNITS, "name": "Untitled sequence", "points": []})

    def _flush(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.path.parent, prefix=".sequences-", suffix=".json")
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(self.items, stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def list(self):
        with self.lock:
            return json.loads(json.dumps(list(self.items.values())))

    def get(self, key):
        with self.lock:
            if key not in self.items:
                raise ValueError("Sequence no longer exists; refresh the library")
            return json.loads(json.dumps(self.items[key]))

    def create(self, value):
        clean = document(value)
        with self.lock:
            key = str(uuid.uuid4())
            self.items[key] = {**clean, "id": key, "revision": 1}
            try:
                self._flush()
            except Exception:
                del self.items[key]
                raise
            return self.get(key)

    def update(self, key, value, revision):
        clean = document(value)
        with self.lock:
            previous = self.get(key)
            if revision != previous["revision"]:
                raise ValueError("This sequence changed in another tab. Refresh before editing.")
            self.items[key] = {**clean, "id": key, "revision": previous["revision"] + 1}
            try:
                self._flush()
            except Exception:
                self.items[key] = previous
                raise
            return self.get(key)
