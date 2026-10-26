"""Teach-and-repeat motion for the SO-101 follower: saved poses, smooth moves, routines.

A pose is a named set of the 6 joint positions (LeRobot units: degrees, gripper 0-100), saved while
the follower mirrors the leader. Routines (pick, place, move a filter, dump the dish) are step lists
built from poses named after the shelf layout in layout.json.

Safety rules the routines follow:
- moves are smooth and speed-limited; going into and out of a slot uses the slow speed, and the
  arm always backs out to the slot's "front" pose, so it retracts the way it went in;
- the arm only turns between the filter shelf and the storage shelf from the pulled-in "carry"
  pose of each side, so it never sweeps a filter through the extrusion;
- after closing on a filter or the dish it checks the gripper didn't close all the way (a missed
  grab); if it did, it opens, backs out and stops;
- with a wrist camera, it reads the filter's ArUco marker from in front of the slot before going in,
  and stops there, gripper open, if it's not the filter asked for.

The inventory (which filter is in which slot, and which one the gripper holds) is kept up to date by
the routines and saved in inventory.json: a slot missing from it hasn't been checked, null is empty,
"?" is a filter whose marker couldn't be read.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
VISION = HERE.parent / "vision"
LAYOUT = HERE / "layout.json"
POSES = HERE / "poses.json"
PRACTICE_POSES = HERE / "practice_poses.json"
INVENTORY = HERE / "inventory.json"
PRACTICE_INVENTORY = HERE / "practice_inventory.json"
FILTERS = VISION / "filters.json"
JOINTS = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]
ARM_JOINTS = JOINTS[:5]
RATE_HZ = 50


class MissedGrab(RuntimeError):
    """The gripper closed (nearly) all the way, so it isn't holding anything."""


class MissingPose(KeyError):
    """A routine needs a pose that hasn't been taught yet."""


class WrongFilter(RuntimeError):
    """The wrist camera saw a different filter in the slot than the one asked for."""


def load_layout():
    return json.loads(LAYOUT.read_text())


def load_poses(path):
    return json.loads(path.read_text()) if path.exists() else {}


def save_poses(poses, path):
    path.write_text(json.dumps(poses, indent=2, sort_keys=True))


def side_of(layout, slot):
    for name, side in layout["sides"].items():
        if slot in side["slots"]:
            return name
    raise ValueError(f"'{slot}' isn't a slot in layout.json; slots are: {', '.join(all_slots(layout))}")


def all_slots(layout):
    return [slot for side in layout["sides"].values() for slot in side["slots"]]


def required_poses(layout):
    """Every pose the routines use, in a sensible teaching order."""
    names = ["rest", "gripper/open", "gripper/closed"]
    for side in layout["sides"].values():
        names.append(side["carry"])
        for slot in side["slots"]:
            names += [f"{slot}/front", f"{slot}/in"]
    for step in layout["dump"]:
        if step[0] == "move" and step[1] not in names:
            names.append(step[1])
    return names


def sleep_until(t):
    delay = t - time.perf_counter()
    if delay > 0:
        time.sleep(delay)


def load_filters():
    return json.loads(FILTERS.read_text())


def filter_label(letter, filters):
    """'A (F1)' for a marker letter; 'empty' for None; '?' for a filter that couldn't be identified."""
    if letter is None:
        return "empty"
    filter_id = filters["codes"].get(letter)
    return f"{letter} ({filter_id})" if filter_id else letter


def letter_for(name, filters):
    """Marker letter of a filter given as its letter (A) or its id (F1)."""
    if name.upper() in filters["markers"]:
        return name.upper()
    for letter, filter_id in filters["codes"].items():
        if filter_id.lower() == name.lower():
            return letter
    raise ValueError(f"unknown filter '{name}': use a letter ({', '.join(filters['markers'])}) or an id like F1")


def load_inventory(path):
    data = json.loads(path.read_text()) if path and path.exists() else {}
    return {"slots": data.get("slots", {}), "holding": data.get("holding")}


def wrist_photo(camera):
    """One frame from the camera named `camera` (see vision/cameras.py). RuntimeError if there's none."""
    if str(VISION) not in sys.path:
        sys.path.insert(0, str(VISION))
    import cv2
    from cameras import open_camera

    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)  # OpenCV's own warnings repeat ours
    try:
        cap = open_camera(camera)
    except SystemExit as e:  # cameras.py reports a missing camera this way
        raise RuntimeError(str(e))
    for _ in range(10):  # let auto-exposure settle
        ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"no picture from camera '{camera}'")
    return frame


def wrist_camera(layout):
    """A function that takes one wrist-camera photo, or None if layout.json names no wrist camera."""
    name = layout.get("wrist_camera")
    return (lambda: wrist_photo(name)) if name else None


class Arm:
    """The follower with smooth, speed-limited moves. Only this object sends it positions."""

    def __init__(self, robot, layout, poses, realtime=True, log=print, camera=None, inventory_path=None):
        self.robot, self.layout, self.poses = robot, layout, poses
        self.realtime, self.log = realtime, log
        self.side = None      # which shelf side the arm is on, once it has gone there through its carry pose
        self.visited = []     # poses reached, most recent last (used to back out of a missed grab)
        self.goal = self.read()
        self.camera = camera  # function returning a wrist-camera frame (see wrist_camera), or None
        self.photo_dir = HERE / "captures"
        self.last_photo = None
        self.filters = load_filters()
        self.inventory_path = inventory_path
        self.inventory = load_inventory(inventory_path)

    def read(self):
        obs = self.robot.get_observation()
        return {j: float(obs[f"{j}.pos"]) for j in JOINTS}

    def send(self, goal):
        self.robot.send_action({f"{j}.pos": v for j, v in goal.items()})
        self.goal = dict(goal)

    def pose(self, name):
        if name not in self.poses:
            raise MissingPose(f"pose '{name}' isn't taught yet (teach it with: save {name})")
        return self.poses[name]

    def move(self, target, speed, joints=ARM_JOINTS):
        """Glide `joints` to `target` at up to `speed` (degrees/s, or %/s for the gripper)."""
        start = dict(self.goal)
        end = {**start, **{j: float(target[j]) for j in joints}}
        distance = max(abs(end[j] - start[j]) for j in joints)
        # smoothstep peaks at 1.5x the average speed, so stretch the move to keep the peak under `speed`
        steps = max(1, int(1.5 * distance / speed * RATE_HZ))
        t0 = time.perf_counter()
        for i in range(1, steps + 1):
            s = i / steps
            s = s * s * (3 - 2 * s)  # ease in and out
            self.send({j: start[j] + (end[j] - start[j]) * s for j in JOINTS})
            if self.realtime:
                sleep_until(t0 + i / RATE_HZ)

    def move_to(self, name, speed="normal"):
        self.log(f"  -> {name}" + (" (slow)" if speed == "slow" else ""))
        self.move(self.pose(name), self.layout["speeds"][speed])
        self.visited.append(name)

    def gripper(self, which):
        self.log(f"  gripper {which}")
        value = self.pose(f"gripper/{'open' if which == 'open' else 'closed'}")["gripper"]
        self.move({"gripper": value}, self.layout["speeds"]["gripper"], ["gripper"])
        if self.realtime:
            time.sleep(0.4)  # let it settle against whatever it's closing on

    def check_grip(self):
        """Raise MissedGrab if the gripper closed (nearly) all the way."""
        opened = self.pose("gripper/open")["gripper"]
        closed = self.pose("gripper/closed")["gripper"]
        travel = (self.read()["gripper"] - opened) / (closed - opened)
        if travel > self.layout["missed_grab_at"]:
            raise MissedGrab(f"the gripper closed {travel:.0%} of the way, so it isn't holding anything")
        self.log(f"  grip ok (closed {travel:.0%} of the way)")

    def go_to_side(self, side):
        """Reach `side`'s carry pose, through the current side's carry pose if switching sides."""
        here = self.layout["sides"][self.side]["carry"] if self.side else None
        if self.side not in (None, side) and self.visited[-1:] != [here]:
            self.move_to(here)
        self.move_to(self.layout["sides"][side]["carry"])
        self.side = side

    def leave_side(self):
        if self.side:
            self.move_to(self.layout["sides"][self.side]["carry"])
            self.side = None

    def shake(self, joint, amplitude, times):
        self.log(f"  shake {joint} +/-{amplitude}")
        centre = dict(self.goal)
        for _ in range(times):
            for offset in (amplitude, -amplitude):
                self.move({**centre, joint: centre[joint] + offset}, self.layout["speeds"]["normal"], [joint])
        self.move(centre, self.layout["speeds"]["normal"], [joint])

    def photo(self, label):
        """A wrist-camera frame, also saved to captures/; None without a working wrist camera."""
        if self.camera is None:
            return None
        try:
            frame = self.camera()
        except RuntimeError as e:
            self.log(f"  wrist camera: {e}; carrying on without it")
            return None
        if self.photo_dir:
            import cv2

            self.last_photo = self.photo_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_{label.replace('/', '-')}.png"
            self.photo_dir.mkdir(exist_ok=True)
            cv2.imwrite(str(self.last_photo), frame)
        return frame

    def capture(self, label):
        """Save a wrist-camera photo (e.g. of a filter just pulled out), if there's a wrist camera."""
        if self.photo(label) is not None and self.photo_dir:
            self.log(f"  photo saved: {self.last_photo.name}")

    def marker_in_view(self, slot):
        """(letter or None, note) for the filter marker nearest the middle of a wrist photo; None without a camera."""
        frame = self.photo(f"{slot}_look")
        if frame is None:
            return None
        if str(VISION) not in sys.path:
            sys.path.insert(0, str(VISION))
        import numpy as np
        from markers import detect

        found = detect(frame)
        if not found:
            return None, "no marker in view"
        centre = np.array([frame.shape[1] / 2, frame.shape[0] / 2])
        marker_id, corners = min(found, key=lambda f: np.linalg.norm(f[1].mean(0) - centre))
        letters = {i: letter for letter, i in self.filters["markers"].items()}
        dx, dy = corners.mean(0) - centre
        return letters.get(marker_id, "?"), f"marker {marker_id}, {dx:+.0f} px across / {dy:+.0f} px down from the middle"

    def label(self, letter):
        return filter_label(letter, self.filters)

    def record(self, slot=None, letter=None, holding=None):
        """Note what's in `slot` and/or what the gripper holds ('' for nothing, None to leave it), and save.

        A filter is in one place only, so once it's seen in `slot`, any other slot noted as holding it goes
        back to 'not checked', and if the gripper was noted as holding it, it holds an unknown filter ('?').
        """
        if slot:
            if letter not in (None, "?"):
                for other, there in list(self.inventory["slots"].items()):
                    if there == letter and other != slot:
                        del self.inventory["slots"][other]
                if self.inventory["holding"] == letter and holding is None:
                    self.inventory["holding"] = "?"
            self.inventory["slots"][slot] = letter
        if holding is not None:
            self.inventory["holding"] = holding or None
        if self.inventory_path:
            self.inventory_path.write_text(json.dumps({**self.inventory, "updated": time.strftime("%Y-%m-%d %H:%M:%S")},
                                                      indent=2))

    def look(self, slot, expect=None, unseen_is_empty=False):
        """From in front of `slot`, read which filter is in it and note it in the inventory.

        Raises WrongFilter if a different filter than `expect` (a marker letter) is there. If no marker is
        seen the slot counts as empty when scanning (unseen_is_empty); otherwise it's left as it was.
        """
        seen = self.marker_in_view(slot)
        if seen is None:
            return
        letter, note = seen
        if letter is None and not unseen_is_empty:
            self.log(f"  {slot}: {note}" + (f"; expected {self.label(expect)}, carrying on" if expect else ""))
            return
        self.log(f"  {slot}: {self.label(letter)} ({note})")
        self.record(slot, letter)
        if expect and letter != expect:
            raise WrongFilter(f"{slot} holds filter {self.label(letter)}, not {self.label(expect)}; nothing was grabbed")

    def took(self, slot):
        self.record(slot, None, holding=self.inventory["slots"].get(slot) or "?")

    def put(self, slot):
        self.record(slot, self.inventory["holding"] or "?", holding="")

    def run(self, steps):
        """Run a routine (a list of steps). On a missed grab: open, back out to the previous pose, stop."""
        for step in steps:
            kind, args = step[0], step[1:]
            if kind == "move":
                self.move_to(args[0], args[1] if len(args) > 1 else "normal")
            elif kind == "open" or kind == "close":
                self.gripper(kind)
            elif kind == "check_grip":
                try:
                    self.check_grip()
                except MissedGrab:
                    self.log("  missed grab: opening and backing out")
                    self.gripper("open")
                    if len(self.visited) >= 2:
                        self.move_to(self.visited[-2], "slow")
                    raise
            elif kind == "side":
                self.go_to_side(args[0])
            elif kind == "leave_side":
                self.leave_side()
            elif kind == "wait":
                if self.realtime:
                    time.sleep(args[0])
            elif kind == "shake":
                self.shake(*args)
            elif kind == "capture":
                self.capture(args[0])
            elif kind == "look":
                self.look(*args)
            elif kind == "scan":
                self.look(args[0], unseen_is_empty=True)
            elif kind == "took":
                self.took(args[0])
            elif kind == "put":
                self.put(args[0])
            else:
                raise ValueError(f"unknown step '{kind}' in {step}")


def check_steps(layout, slot):
    """Dry run with the gripper open: in and back out, to check a slot's poses line up."""
    side = side_of(layout, slot)
    return [["side", side], ["open"], ["move", f"{slot}/front"], ["move", f"{slot}/in", "slow"], ["wait", 1],
            ["move", f"{slot}/front", "slow"], ["move", layout["sides"][side]["carry"]]]


def pick_steps(layout, slot, expect=None):
    """Take the filter out of `slot`; with `expect` (a marker letter), only if it's that filter."""
    side = side_of(layout, slot)
    return [["side", side], ["open"], ["move", f"{slot}/front"], ["look", slot, expect], ["move", f"{slot}/in", "slow"],
            ["close"], ["check_grip"], ["took", slot], ["move", f"{slot}/front", "slow"], ["capture", slot],
            ["move", layout["sides"][side]["carry"]]]


def place_steps(layout, slot):
    side = side_of(layout, slot)
    return [["side", side], ["move", f"{slot}/front"], ["move", f"{slot}/in", "slow"], ["open"], ["put", slot],
            ["move", f"{slot}/front", "slow"], ["move", layout["sides"][side]["carry"]]]


def transfer_steps(layout, src, dst, expect=None):
    return pick_steps(layout, src, expect) + place_steps(layout, dst)


def scan_steps(layout):
    """Read every slot's marker from in front of it, going back to the carry pose between slots."""
    steps = []
    for name, side in layout["sides"].items():
        steps.append(["side", name])
        for slot in side["slots"]:
            steps += [["move", f"{slot}/front"], ["scan", slot], ["move", side["carry"]]]
    return steps


def dump_steps(layout):
    return [["leave_side"]] + layout["dump"]


def finish_steps():
    return [["leave_side"], ["move", "rest"]]


def connect(follower_port, follower_id, leader_port=None, leader_id=None, practice=False):
    """Connect the follower (and the leader, for teaching). With practice=True, stand-ins are used."""
    if practice:
        return PracticeFollower(), PracticeLeader() if leader_port else None
    from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig

    follower = SO101Follower(SO101FollowerConfig(port=follower_port, id=follower_id))
    # Set every goal to the present position before torque comes on, so the arm doesn't jump to an
    # old goal left over from a previous session. Same steps as follower.connect() otherwise.
    follower.bus.connect()
    if not follower.is_calibrated:
        raise SystemExit("follower calibration doesn't match its file; run lerobot-calibrate first")
    follower.bus.sync_write("Goal_Position", follower.bus.sync_read("Present_Position"))
    follower.configure()

    leader = None
    if leader_port:
        from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig

        leader = SO101Leader(SO101LeaderConfig(port=leader_port, id=leader_id))
        leader.connect()
    return follower, leader


class PracticeFollower:
    """Stands in for the follower: reaches every goal instantly; the gripper can be told to stop on an object."""

    def __init__(self):
        self.position = {j: 0.0 for j in JOINTS}
        self.object_at = None  # gripper value where it meets an object when closing, or None for empty
        self.closing_up = True  # whether closing means the gripper value goes up

    def get_observation(self):
        return {f"{j}.pos": v for j, v in self.position.items()}

    def send_action(self, action):
        for key, value in action.items():
            joint = key.removesuffix(".pos")
            if joint == "gripper" and self.object_at is not None:
                past = value > self.object_at if self.closing_up else value < self.object_at
                value = self.object_at if past else value
            self.position[joint] = value
        return action

    def disconnect(self):
        pass


class PracticeLeader:
    """Stands in for the leader: reports whatever position it's set to."""

    def __init__(self):
        self.position = {j: 0.0 for j in JOINTS}

    def get_action(self):
        return {f"{j}.pos": v for j, v in self.position.items()}

    def disconnect(self):
        pass
