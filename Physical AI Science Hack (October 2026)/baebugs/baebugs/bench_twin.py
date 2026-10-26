"""Bench digital twin: a stateful 3D resource tree (PyLabRobot), in the spirit of
Google Research's VERID, with Merkle-hashed state after every action.

Tree (PyLabRobot `Resource`s; sizes and locations in mm):
  bench
   |- linear_rail                      (x axis, front of the bench)
   |   '- arm_carriage                 (Partabot arm; reach envelope, fork tool)
   |- tower                            (wood post + cantilevered rail arms)
   |   |- post
   |   |- storage_face_L{0..n}         (slot = rail-arm pair; tray slides along -x)
   |   '- filter_face_L{0..n}          (slot; tray slides along +x; staggered half a pitch)
   |        '- tray:<id>               (2x3 printed frame; cells; filter insert; contents)
   |             |- filter:<id>        (hole spec hash from punch_filters / kit)
   |             '- cell_r{r}c{c}
   |- bench_rack_R{0..}                (overflow trays)
   '- camera_station
Geometry comes from config/tower.yaml (MEASURE placeholders until the tower is built);
BugPicker's GPL tray meshes are loaded from a BugPicker checkout at run time (not
vendored) and their sha256 recorded.

Every action (fetch / insert / pull / image / return / pour / rinse) runs checks,
each a hashed claim: target reachable from the arm on the rail, slot free/occupied as
required, the tray's swept slide volume clears every other body, the fork clears the
trays above and below, stack order coarse->fine. Then the state tree is hashed
(Merkle over every node's name, absolute box and state) and appended to an MMR: a run
is a provable sequence of bench states. Any failed check stops the run (fail closed).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .explore import merkle_root
from .mmr import MMRLog
from .sieve import load_yaml

H = lambda o: hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
TRAY_H = 14.0          # mm, printed frame height (BugPicker tray.stl is 12.5)
RAIL_STRIP = (12.0, 6.0)   # plywood rail-arm cross-section (MEASURE)


def _R():
    from pylabrobot.resources import Coordinate, Resource
    return Resource, Coordinate


class BenchTwin:
    def __init__(self, cfg=None, inventory=None, bugpicker_dir=None, log_path=None):
        from . import tower_twin as TT
        Resource, C = _R()
        self.cfg = cfg or load_yaml("tower.yaml")
        self.inv = inventory or TT.tower_inventory()
        T, A = self.cfg["tower"], self.cfg["arm"]
        fw, fd = self.cfg["tray"]["footprint_mm"]          # tray: x (slide direction) = depth fd, y = width fw
        self.tray_dims = (fd, fw, TRAY_H)
        self.mesh_evidence = self._bugpicker_meshes(bugpicker_dir)
        self.bench = Resource("bench", 1200, 600, 20, category="bench")
        self.bench.location = C(0, 0, 0)                     # root of the resource tree
        self.rail = Resource("linear_rail", A["rail_length_mm"], 40, 30, category="rail")
        self.bench.assign_child_resource(self.rail, location=C(0, 0, 20))
        self.carriage = Resource("arm_carriage", 80, 40, 60, category="arm")
        self.rail.assign_child_resource(self.carriage, location=C(0, 0, 30))
        self.tower_y = 40 + A["reach_mm"] * 0.55                  # tower centre line behind the rail
        px, py = T["post_mm"]
        top = T["first_level_z_mm"] + T["levels_per_face"] * T["level_pitch_mm"] + T["stagger_mm"] + 40
        self.tower = Resource("tower", px + 2 * (fd + 20), fw + 40, top, category="tower")
        self.tower_x0 = T["x_mm"] - self.tower.get_size_x() / 2
        self.bench.assign_child_resource(self.tower, location=C(self.tower_x0, self.tower_y - self.tower.get_size_y() / 2, 20))
        self.post = Resource("post", px, py, top, category="post")
        self.tower.assign_child_resource(self.post, location=C(self.tower.get_size_x() / 2 - px / 2,
                                                               self.tower.get_size_y() / 2 - py / 2, 0))
        self.slots = {}
        for face, sign in (("storage", -1), ("filter", +1)):
            for lv in range(T["levels_per_face"]):
                z = T["first_level_z_mm"] + lv * T["level_pitch_mm"] + (T["stagger_mm"] if face == "filter" else 0)
                x = self.tower.get_size_x() / 2 + sign * (px / 2 + 2) + (0 if sign > 0 else -fd)
                s = Resource(f"{face}_face_L{lv}", fd, fw, TRAY_H, category=f"slot:{face}")
                self.tower.assign_child_resource(s, location=C(x, 20, z))
                self.slots[(face, lv)] = s
        self.rack = []
        for i in range(self.cfg["bench_rack"]["slots"]):
            r = Resource(f"bench_rack_R{i}", fd, fw, TRAY_H, category="slot:rack")
            self.bench.assign_child_resource(r, location=C(self.cfg["bench_rack"]["x_mm"] + (i % 3) * (fd + 10),
                                                           self.tower_y + (i // 3) * (fw + 10), 20))
            self.rack.append(r)
        self.camera = Resource("camera_station", 60, 60, self.cfg["camera_station"]["z_mm"], category="camera")
        self.bench.assign_child_resource(self.camera, location=C(self.cfg["camera_station"]["x_mm"], 60, 20))
        self.state = {"holding": None, "water_l": load_yaml("sieves.yaml")["water"]["reservoir_l"], "contents": {}}
        self.trays = {}
        self._load_inventory()
        self.log = MMRLog(log_path) if log_path else None
        self.events = []

    # ------------------------------------------------------------ build
    def _bugpicker_meshes(self, d):
        ev = {}
        if d:
            import trimesh
            for f in ("Designs/tray.stl", "Designs/screentray.stl"):
                p = Path(d, f)
                if p.exists():
                    m = trimesh.load(p)
                    ev[f] = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                             "extents_mm": [round(float(e), 1) for e in m.bounding_box.extents], "license": "GPL-3.0 (BugPicker)"}
        return ev

    def _make_tray(self, item):
        Resource, C = _R()
        fd, fw, h = self.tray_dims
        t = Resource(f"tray:{item['id']}", fd, fw, h, category="tray")
        if item.get("entry"):
            from . import punch_filters as PF
            f = Resource(f"filter:{item['id']}", fd - 8, fw - 8, 1.6, category="filter")
            t.assign_child_resource(f, location=C(4, 4, 2))
            f.spec = PF.spec(item["entry"])
        for r in range(2):
            for c in range(3):
                t.assign_child_resource(Resource(f"cell_r{r}c{c}:{item['id']}", (fd - 8) / 3, (fw - 8) / 2, h - 2,
                                                 category="cell"), location=C(4 + c * (fd - 8) / 3, 4 + r * (fw - 8) / 2, 2))
        return t

    def _load_inventory(self):
        _, C = _R()
        catch = next((f for f in self.inv if f["kind"] == "catch"), None)
        storage = [self.slots[("storage", l)] for l in range(self.cfg["tower"]["levels_per_face"])] + self.rack
        k = 0
        for item in self.inv:
            t = self._make_tray(item)
            self.trays[item["id"]] = t
            if item is catch:
                self.slots[("filter", self.cfg["tower"]["filter_face"]["catch_level"])].assign_child_resource(t, location=C(0, 0, 0))
            elif k < len(storage):
                storage[k].assign_child_resource(t, location=C(0, 0, 0)); k += 1

    # ------------------------------------------------------------ geometry helpers
    @staticmethod
    def box(res):
        a = res.get_absolute_location()
        return np.array([[a.x, a.y, a.z], [a.x + res.get_size_x(), a.y + res.get_size_y(), a.z + res.get_size_z()]])

    @staticmethod
    def overlap(b1, b2, tol=0.5):
        return bool(np.all(b1[0] < b2[1] - tol) and np.all(b2[0] < b1[1] - tol))

    def slot_of(self, tray_id):
        t = self.trays[tray_id]
        return t.parent

    def _face(self, slot):
        return "filter" if slot.category == "slot:filter" else "storage" if slot.category == "slot:storage" else "rack"

    def handle_point(self, slot):
        b = self.box(slot)
        face = self._face(slot)
        x = b[0][0] if face == "storage" else b[1][0] if face == "filter" else (b[0][0] + b[1][0]) / 2
        return np.array([x, (b[0][1] + b[1][1]) / 2, b[0][2] + TRAY_H / 2])

    def reach_ok(self, point):
        A = self.cfg["arm"]
        dy, dz = point[1] - 20.0, point[2] - (20 + 30 + 60)
        horiz = math.hypot(dy, dz)
        return {"reach_needed_mm": round(horiz, 1), "reach_mm": A["reach_mm"],
                "z_ok": A["min_z_mm"] <= point[2] <= A["max_z_mm"], "pass": horiz <= A["reach_mm"] and A["min_z_mm"] <= point[2] <= A["max_z_mm"]}

    def swept_clear(self, tray_id, slot):
        """Box swept by the tray sliding out of / into `slot` along x must not hit any other body."""
        b = self.box(slot)
        face, d = self._face(slot), self.cfg["tray"]["insert_depth_mm"]
        sweep = b.copy()
        if face == "storage":
            sweep[0][0] -= d
        elif face == "filter":
            sweep[1][0] += d
        else:
            sweep[1][2] += 40
        hits = []
        for other_id, t in self.trays.items():
            if other_id != tray_id and t.parent is not None and t.parent is not slot and self.overlap(sweep, self.box(t)):
                hits.append(other_id)
        if self.overlap(sweep, self.box(self.post)):
            hits.append("post")
        return {"hits": hits, "pass": not hits}

    def fork_clear(self, slot):
        """Fork (30 x 60 x 10 mm under the handle) must clear trays in neighbouring levels."""
        p = self.handle_point(slot)
        fork = np.array([[p[0] - 15, p[1] - 30, p[2] - TRAY_H / 2 - 10], [p[0] + 15, p[1] + 30, p[2] - TRAY_H / 2]])
        hits = [tid for tid, t in self.trays.items() if t.parent is not None and t.parent is not slot
                and self.overlap(fork, self.box(t))]
        return {"hits": hits, "pass": not hits}

    # ------------------------------------------------------------ state hash
    def state_root(self):
        leaves = []
        def walk(r):
            b = self.box(r)
            leaves.append(H({"name": r.name, "box": np.round(b, 2).tolist(), "category": r.category,
                             "parent": r.parent.name if r.parent else None}))
            for c in r.children:
                walk(c)
        walk(self.bench)
        leaves.append(H({"state": self.state}))
        return merkle_root(sorted(leaves))

    # ------------------------------------------------------------ actions
    def _record(self, action, params, checks):
        ok = all(c.get("pass", True) for c in checks.values())
        ev = {"action": action, "params": params, "checks": checks, "pass": ok, "state_root": self.state_root() if ok else None}
        ev["leaf"] = H(ev)
        self.events.append(ev)
        if self.log:
            self.log.append(ev)
        if not ok:
            raise RuntimeError(f"{action} {params}: failed checks {[k for k, c in checks.items() if not c.get('pass', True)]}")
        return ev

    def fetch(self, tray, from_storage=None):
        slot = self.slot_of(tray)
        checks = {"holding_free": {"pass": self.state["holding"] is None},
                  "reach": self.reach_ok(self.handle_point(slot)), "fork": self.fork_clear(slot),
                  "sweep": self.swept_clear(tray, slot)}
        if all(c["pass"] for c in checks.values()):
            slot.unassign_child_resource(self.trays[tray]); self.state["holding"] = tray
        return self._record("fetch", {"tray": tray, "slot": slot.name}, checks)

    def insert(self, tray, filter_slot):
        _, C = _R()
        slot = self.slots[("filter", filter_slot)]
        checks = {"holding_this": {"pass": self.state["holding"] == tray}, "slot_free": {"pass": not slot.children},
                  "reach": self.reach_ok(self.handle_point(slot)), "fork": self.fork_clear(slot),
                  "sweep": self.swept_clear(tray, slot), "order": self._order_check(tray, filter_slot)}
        if all(c["pass"] for c in checks.values()):
            slot.assign_child_resource(self.trays[tray], location=C(0, 0, 0)); self.state["holding"] = None
        return self._record("insert", {"tray": tray, "slot": slot.name}, checks)

    def _order_check(self, tray, level):
        ap = {f["id"]: f.get("metrics", {}).get("inscribed_d_mm", 0.0) for f in self.inv}
        above = [ap[c.name.split(":", 1)[1]] for (face, lv), s in self.slots.items() if face == "filter" and lv > level
                 for c in s.children]
        below = [ap[c.name.split(":", 1)[1]] for (face, lv), s in self.slots.items() if face == "filter" and lv < level
                 for c in s.children if ap[c.name.split(":", 1)[1]] > 0]
        me = ap[tray]
        return {"pass": all(a >= me for a in above) and all(b <= me for b in below), "aperture_mm": me}

    def pull(self, tray, filter_slot):
        slot = self.slots[("filter", filter_slot)]
        checks = {"holding_free": {"pass": self.state["holding"] is None},
                  "present": {"pass": any(c is self.trays[tray] for c in slot.children)},
                  "reach": self.reach_ok(self.handle_point(slot)), "fork": self.fork_clear(slot),
                  "sweep": self.swept_clear(tray, slot)}
        if all(c["pass"] for c in checks.values()):
            slot.unassign_child_resource(self.trays[tray]); self.state["holding"] = tray
        return self._record("pull", {"tray": tray, "slot": slot.name}, checks)

    def image(self, tray):
        cam = self.box(self.camera)
        p = np.array([(cam[0][0] + cam[1][0]) / 2, (cam[0][1] + cam[1][1]) / 2, cam[1][2]])
        return self._record("image", {"tray": tray}, {"holding_this": {"pass": self.state["holding"] == tray},
                                                      "reach": self.reach_ok(p)})

    def put_back(self, tray, to):
        _, C = _R()
        if to.startswith("filter level"):
            slot = self.slots[("filter", int(to.split()[-1]))]
        elif to.startswith("R"):
            slot = self.rack[int(to[1:])]
        else:
            slot = self.slots[("storage", int(to[1:]))]
        checks = {"holding_this": {"pass": self.state["holding"] == tray}, "slot_free": {"pass": not slot.children},
                  "reach": self.reach_ok(self.handle_point(slot)), "fork": self.fork_clear(slot),
                  "sweep": self.swept_clear(tray, slot)}
        if all(c["pass"] for c in checks.values()):
            slot.assign_child_resource(self.trays[tray], location=C(0, 0, 0)); self.state["holding"] = None
        return self._record("return", {"tray": tray, "slot": slot.name}, checks)

    def pour(self, z_mm):
        return self._record("pour", {"z_mm": z_mm}, {"reach": self.reach_ok(np.array([self.cfg["tower"]["x_mm"], self.tower_y, z_mm]))})

    def rinse(self, litres):
        ok = self.state["water_l"] - litres >= load_yaml("sieves.yaml")["water"]["min_reserve_l"]
        if ok:
            self.state["water_l"] = round(self.state["water_l"] - litres, 3)
        return self._record("rinse", {"litres": litres}, {"water": {"pass": ok, "left_l": self.state["water_l"]}})

    def run_actions(self, actions):
        """Execute tower_twin.actions_for output; fail closed on the first failed check
        (that action is the run's break point; nothing after it is attempted)."""
        try:
            self._run(actions)
            status, bp = "EXECUTED", None
        except RuntimeError as e:
            status, bp = "STOPPED_AT_BREAK_POINT", {"event": len(self.events) - 1, "detail": str(e),
                                                     "checks": self.events[-1]["checks"] if self.events else None}
        return {"status": status, "break_point": bp, "actions": len(self.events),
                "final_state_root": self.state_root(), "event_root": merkle_root([e["leaf"] for e in self.events])}

    def _run(self, actions):
        for a, p in actions:
            if a == "fetch":
                self.fetch(p["tray"])
            elif a == "insert":
                self.insert(p["tray"], p["filter_slot"])
            elif a == "pour":
                self.pour(p["z_mm"])
            elif a == "rinse":
                self.rinse(p["litres"])
            elif a == "pull":
                self.pull(p["tray"], p["filter_slot"])
            elif a == "image":
                self.image(p["tray"])
            elif a == "return":
                self.put_back(p["tray"], p["to"] if p["to"] else "A0")

    # ------------------------------------------------------------ export
    def scene(self, include_trays=True):
        import trimesh
        meshes = []
        def add(res, color):
            b = self.box(res); m = trimesh.creation.box(extents=b[1] - b[0])
            m.apply_translation((b[0] + b[1]) / 2); m.visual.face_colors = color; meshes.append(m)
        add(self.bench, [222, 200, 160, 255]); add(self.rail, [40, 40, 40, 255]); add(self.post, [150, 100, 60, 255])
        add(self.camera, [60, 60, 200, 255]); add(self.carriage, [230, 120, 20, 255])
        _sx, sy = RAIL_STRIP
        for s in self.slots.values():
            b = self.box(s)
            for y in (b[0][1] - sy, b[1][1]):
                m = trimesh.creation.box(extents=[b[1][0] - b[0][0], sy, 6]); m.apply_translation([(b[0][0] + b[1][0]) / 2, y + sy / 2, b[0][2] - 3])
                m.visual.face_colors = [200, 170, 120, 255]; meshes.append(m)
        if include_trays:
            for t in self.trays.values():
                if t.parent is not None:
                    add(t, [245, 245, 245, 255])
        return trimesh.Scene(meshes)

    def tower_scad(self):
        T = self.cfg["tower"]; fd, fw, _ = self.tray_dims; px, py = T["post_mm"]; sx, sy = RAIL_STRIP
        lines = ["// baebugs wood tower: post + cantilevered rail arms (generated from config/tower.yaml; MEASURE values)",
                 f"post = [{px}, {py}, {self.post.get_size_z()}]; tray = [{fd}, {fw}]; strip = [{sx}, {sy}];",
                 "cube(post);"]
        for (face, lv), s in self.slots.items():
            a = s.get_absolute_location(); z = a.z - self.tower.get_absolute_location().z - 6
            x0 = px if face == "filter" else -fd
            for yy in (py / 2 - fw / 2 - sy, py / 2 + fw / 2):
                lines.append(f"translate([{x0:.1f}, {yy:.1f}, {z:.1f}]) cube([{fd + px if face == 'storage' else fd:.1f}, strip[1], 6]);  // {face} L{lv}")
        return "\n".join(lines) + "\n"


def preview_png(twin, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(9, 6)); ax = fig.add_subplot(111, projection="3d")
    sc = twin.scene()
    for g in sc.geometry.values():
        tri = g.vertices[g.faces]
        col = tuple(float(x) for x in g.visual.face_colors[0][:3] / 255.0)
        ax.add_collection3d(Poly3DCollection(tri, facecolor=col, edgecolor="none", alpha=0.9))
    b = sc.bounds; c = b.mean(0); r = (b[1] - b[0]).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(0, 2 * r * 0.6)
    ax.view_init(22, -60); ax.set_axis_off()
    ax.set_title("baebugs bench twin (placeholder geometry: config/tower.yaml MEASURE)", fontsize=9)
    plt.tight_layout(); plt.savefig(path, dpi=110)


def main(argv=None):
    import argparse

    from . import tower_twin as TT
    ap = argparse.ArgumentParser("baebugs-bench-twin")
    ap.add_argument("--out", default="print/bench")
    ap.add_argument("--bugpicker", help="path to a BugPicker checkout (tray meshes are GPL, not vendored)")
    ap.add_argument("--tiers", type=int, default=2)
    a = ap.parse_args(argv)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    tw = BenchTwin(bugpicker_dir=a.bugpicker, log_path=out / "demo_run_mmr.jsonl")
    if (out / "demo_run_mmr.jsonl").exists() and tw.log.records:
        (out / "demo_run_mmr.jsonl").unlink(); tw.log = MMRLog(out / "demo_run_mmr.jsonl")
    tw.scene().export(out / "bench.glb")
    (out / "tower.scad").write_text(tw.tower_scad())
    (out / "bench_plr.json").write_text(json.dumps(tw.bench.serialize(), indent=1, default=str))
    preview_png(tw, out / "bench_preview.png")
    r0 = tw.state_root()
    plan = TT.plan_tiers(TT.demo_objects(), TT.tower_inventory(), TT.load_yaml("tower.yaml"), a.tiers)
    st = TT.initial_state(TT.load_yaml("tower.yaml"), TT.tower_inventory())
    acts = TT.actions_for(plan["best"], TT.load_yaml("tower.yaml"), st)
    res = tw.run_actions(acts)
    summary = {"initial_state_root": r0, **res, "plan": plan["best"]["tiers"], "mesh_evidence": tw.mesh_evidence,
               "mmr_root": tw.log.mmr.root, "geometry_status": "PLACEHOLDER (MEASURE)"}
    (out / "demo_run.json").write_text(json.dumps({"summary": summary, "events": tw.events}, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == "__main__":
    main()
