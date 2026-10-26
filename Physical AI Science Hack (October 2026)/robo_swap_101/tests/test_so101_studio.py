"""Planner, persistence, API and motion interlocks; never open a real serial port."""
import copy
import http.client
import json
import math
import shutil
import subprocess
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from so101_studio.devices import Simulation
from so101_studio.filtering import TELEOP_RELATIVE_LIMITS, TargetFilter, limit_relative_target
from so101_studio.model import HOME, JOINTS, LIMITS, ROOT, URDF, Store, UNITS, document, pose
from so101_studio.kinematics import CHAIN, forward
from so101_studio.planner import Plan
from so101_studio.runtime import CONTROL_FPS, PERIOD, Runtime
from so101_studio.server import StudioServer


def point(label="Pick", angle=20, source="simulation", calibration=None):
    return {"id": label, "name": label, "pose": {**HOME, "shoulder_pan": angle},
            "dwell": 0.25, "source": source, "calibration": calibration}


def sequence(points=None):
    return {"version": 1, "units": UNITS, "name": "Test sequence", "points": points or []}


def pickup(label="Pickup tip"):
    return {"id": label, "name": label, "kind": "pickup_tip"}


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds=1 / 30):
        self.now += seconds
        return self.now


class FakeHardware(Simulation):
    mode = "hardware"
    calibration = "calibration-A"
    has_leader = True

    def __init__(self, *args):
        super().__init__()
        self.commands = []
        self.leader_position = {**HOME, "shoulder_pan": 40.0}
        self.fail_read = False
        self.track = True

    def read(self):
        if self.fail_read:
            raise IOError("USB disconnected")
        return super().read()

    def send(self, target):
        self.commands.append(target.copy())
        if self.track:
            super().send(target)

    def leader(self):
        return self.leader_position.copy()


class FilterTests(unittest.TestCase):
    def test_relative_limits_bound_all_joints_and_reject_invalid_feedback(self):
        for sign in (-1, 1):
            target = {j: HOME[j] + sign * 1000 for j in JOINTS}
            result = limit_relative_target(target, HOME)
            self.assertEqual(result, {j: HOME[j] + sign * TELEOP_RELATIVE_LIMITS[j] for j in JOINTS})
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            limit_relative_target({**HOME, 'wrist_flex': float('nan')}, HOME)
        with self.assertRaisesRegex(ValueError, 'must match'):
            limit_relative_target({}, HOME)

    def test_cli_filter_time_constant_deadband_and_accepted_target_feedback(self):
        filtered = TargetFilter(tau=.06, deadband=.2, speed=80)
        observation = {'elbow_flex.pos': 10., 'gripper.pos': 35.}
        first = filtered.apply({'elbow_flex.pos': 11., 'gripper.pos': 35.1}, observation, 100.)
        self.assertAlmostEqual(first['elbow_flex.pos'], 10 + (1 - math.exp(-(1 / 30) / .06)))
        self.assertEqual(first['gripper.pos'], 35.)
        # The driver may accept less than the requested target; use that result.
        filtered.accept({'elbow_flex.pos': 10.1, 'gripper.pos': 35.})
        second = filtered.apply({'elbow_flex.pos': 11.}, observation, 100. + 1 / 60)
        self.assertAlmostEqual(second['elbow_flex.pos'], 10.1 + .9 * (1 - math.exp(-(1 / 60) / .06)))

    def test_cli_filter_slew_cap_stall_cap_and_invalid_feedback(self):
        filtered = TargetFilter()
        first = filtered.apply({'shoulder_pan.pos': 100.}, {'shoulder_pan.pos': 0.}, 100.)
        self.assertAlmostEqual(first['shoulder_pan.pos'], 80 / 30)
        filtered.accept(first)
        second = filtered.apply({'shoulder_pan.pos': 100.}, {}, 100. + 1 / 60)
        self.assertAlmostEqual(second['shoulder_pan.pos'] - first['shoulder_pan.pos'], 80 / 60)
        filtered.accept(second)
        delayed = filtered.apply({'shoulder_pan.pos': 100.}, {}, 101.)
        self.assertAlmostEqual(delayed['shoulder_pan.pos'] - second['shoulder_pan.pos'], 80 / 30)
        with self.assertRaisesRegex(ValueError, 'Non-finite'):
            filtered.apply({'shoulder_pan.pos': float('nan')}, {}, 102.)
        with self.assertRaisesRegex(ValueError, 'Missing finite'):
            TargetFilter().apply({'elbow_flex.pos': 1}, {}, 102.)


class PlannerTests(unittest.TestCase):
    def test_path_passes_through_every_target_and_holds_without_overshoot(self):
        points = [point("A", 35), point("B", -15), point("C", 0)]
        plan = Plan(HOME, points, 12, 24)
        for segment in plan.segments:
            self.assertEqual(plan.at(segment["start"])[0], segment["from"])
            for offset in (segment["move"], segment["move"] + segment["dwell"] / 2):
                self.assertEqual(plan.at(segment["start"] + offset)[0], segment["to"])
        for i in range(5001):
            p, index = plan.at(plan.duration * i / 5000)
            s = plan.segments[index]
            for joint in JOINTS:
                self.assertGreaterEqual(p[joint] + 1e-10, min(s["from"][joint], s["to"][joint]))
                self.assertLessEqual(p[joint] - 1e-10, max(s["from"][joint], s["to"][joint]))
        self.assertEqual(plan.at(plan.duration + 100)[0], points[-1]["pose"])

    def test_numerical_velocity_acceleration_and_stationary_endpoints(self):
        plan = Plan(HOME, [point(angle=85)], 17, 31)
        duration = plan.segments[0]["move"]
        dt = duration / 10000
        samples = [plan.at(i * dt)[0]["shoulder_pan"] for i in range(10001)]
        velocity = [(b - a) / dt for a, b in zip(samples, samples[1:])]
        acceleration = [(b - a) / dt for a, b in zip(velocity, velocity[1:])]
        self.assertLessEqual(max(map(abs, velocity)), 17.0001)
        self.assertLessEqual(max(map(abs, acceleration)), 31.0001)
        self.assertLess(abs(velocity[0]), 0.0001)
        self.assertLess(abs(velocity[-1]), 0.0001)

    def test_stationary_pose_and_gripper_are_planned(self):
        p = point(angle=0)
        p["pose"]["gripper"] = 90
        plan = Plan(HOME, [p, p], 10, 20)
        self.assertEqual(plan.at(plan.duration)[0]["gripper"], 90)
        self.assertGreater(plan.duration, 10)

    def test_invalid_inputs_and_calibrated_limits(self):
        for bad in (float("nan"), float("inf"), True, "20", -1):
            with self.assertRaises(ValueError):
                Plan(HOME, [point()], speed=bad)
        with self.assertRaises(ValueError):
            Plan(HOME, [])
        with self.assertRaises(ValueError):
            Plan(HOME, [point(angle=500)])
        with self.assertRaises(ValueError):
            Plan(HOME, [point(angle=50)], limits={**LIMITS, "shoulder_pan": (-20, 20)})
        with self.assertRaises(ValueError):
            Plan(HOME, [point(str(i), 100 if i % 2 else -100) for i in range(200)], speed=1)

    def test_limit_error_identifies_the_offending_saved_position(self):
        home = point('Home', source='hardware')
        home['pose']['shoulder_lift'] = -101.31868131868131
        with self.assertRaisesRegex(ValueError, "Position 'Home' .*shoulder_lift"):
            Plan(HOME, [home])

    def test_browser_and_server_evaluate_identical_trajectories(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required to compare browser interpolation")
        plan = Plan(HOME, [point("A", 31), pickup(), point("B", -16)])
        times = [0, 0.1, plan.segments[0]["move"], plan.segments[1]["start"], plan.duration, plan.duration + 10]
        times += [plan.duration * i / 100 for i in range(101)]
        times += [segment["start"] + segment["move"] * u for segment in plan.segments
                  for u in (0, 1e-9, .25, .5, .75, 1 - 1e-9, 1)]
        script = "import {samplePlan} from './robot_viewer/src/motion.js'; let s=''; for await (const c of process.stdin) s+=c; const {plan,times}=JSON.parse(s); console.log(JSON.stringify(times.map(t=>samplePlan(plan,t))));"
        result = subprocess.run([node, "--input-type=module", "-e", script], cwd=ROOT, check=True,
                                input=json.dumps({"plan": plan.public(), "times": times}), text=True, capture_output=True)
        for t, output in zip(times, json.loads(result.stdout)):
            expected, index = plan.at(t)
            self.assertEqual(index, output["index"])
            for joint in JOINTS:
                self.assertAlmostEqual(output["pose"][joint], expected[joint], places=10)


class PickupTests(unittest.TestCase):
    def test_vertical_distance_orientation_and_return_at_rotated_poses(self):
        approaches = [HOME, {**HOME, 'shoulder_pan': 43, 'shoulder_lift': -51,
                            'elbow_flex': 20, 'wrist_flex': 65, 'wrist_roll': 71, 'gripper': 26}]
        for approach in approaches:
            plan = Plan(approach, [pickup()])
            origin, orientation = forward(approach)
            down, up = plan.segments
            bottom, _ = forward(plan.at(up['start'])[0])
            self.assertAlmostEqual(bottom[2] - origin[2], -.003, places=7)
            last_z = origin[2]
            for i in range(1001):
                current, index = plan.at(plan.duration * i / 1000)
                xyz, r = forward(current)
                self.assertLess(math.hypot(xyz[0] - origin[0], xyz[1] - origin[1]), 1e-6)
                self.assertLess(max(abs(a - b) for row, expected in zip(r, orientation) for a, b in zip(row, expected)), 2e-5)
                self.assertEqual(current['gripper'], approach['gripper'])
                self.assertLessEqual(xyz[2], origin[2] + 1e-7)
                self.assertGreaterEqual(xyz[2], origin[2] - .003 - 1e-7)
                if index == 0:
                    self.assertLessEqual(xyz[2], last_z + 1e-9)
                elif i > 501:
                    self.assertGreaterEqual(xyz[2], last_z - 1e-9)
                last_z = xyz[2]
            self.assertEqual(plan.at(plan.duration)[0], approach)

    def test_action_resolves_from_preceding_pose_after_reordering(self):
        a, b = point('A', 30), point('B', -25)
        for points, expected in (([a, pickup(), b], a['pose']), ([b, pickup(), a], b['pose'])):
            plan = Plan(HOME, points)
            down, up = plan.segments[1:3]
            self.assertEqual(down['from'], expected)
            self.assertEqual(up['to'], expected)
            self.assertEqual(plan.segments[3]['from'], expected)
            self.assertEqual([s['step_index'] for s in plan.segments], [0, 1, 1, 2])

    def test_cartesian_spline_respects_joint_speed_and_acceleration(self):
        plan = Plan(HOME, [pickup()], speed=1, acceleration=1)
        dt = plan.duration / 10000
        samples = [plan.at(i * dt)[0] for i in range(10001)]
        for joint in JOINTS:
            values = [sample[joint] for sample in samples]
            speeds = [(b - a) / dt for a, b in zip(values, values[1:])]
            accelerations = [(b - a) / dt for a, b in zip(speeds, speeds[1:])]
            self.assertLessEqual(max(map(abs, speeds)), 1.0001)
            self.assertLessEqual(max(map(abs, accelerations)), 1.0001)
            self.assertLess(abs(speeds[0]), .0001)
            self.assertLess(abs(speeds[-1]), .0001)
            self.assertGreaterEqual(min(values), LIMITS[joint][0])
            self.assertLessEqual(max(values), LIMITS[joint][1])

    def test_joint_limit_blocks_full_action_with_named_error(self):
        limits = {**LIMITS, 'elbow_flex': (-.1, .1)}
        with self.assertRaisesRegex(ValueError, "Pickup step 'Insert tip'.*elbow_flex"):
            Plan(HOME, [pickup('Insert tip')], limits=limits)

    def test_recipe_roundtrip_edit_and_unknown_kind_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'sequences.json'
            store = Store(path)
            doc = store.create(sequence([point(), pickup()]))
            doc['points'].reverse()
            doc['points'][0]['name'] = 'Insert tip'
            saved = store.update(doc['id'], doc, doc['revision'])
            self.assertEqual(Store(path).get(doc['id']), saved)
            self.assertEqual(saved['points'][0], {**pickup(), 'name': 'Insert tip'})
            doc['points'][0]['kind'] = 'unknown'
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                document(doc)

    def test_kinematics_match_browser_urdf_joint_transforms(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required to compare the visualizer transforms')
        joints = {j.attrib['name']: j for j in ET.parse(URDF).getroot().findall('joint')}
        chain = []
        for name, *_ in CHAIN:
            joint = joints[name]
            chain.append({'name': name, 'type': joint.attrib['type'],
                          'xyz': list(map(float, joint.find('origin').attrib['xyz'].split())),
                          'rpy': list(map(float, joint.find('origin').attrib['rpy'].split())),
                          'axis': list(map(float, joint.find('axis').attrib['xyz'].split()))})
        poses = [HOME, {**HOME, 'shoulder_pan': 31, 'shoulder_lift': -101.3,
                       'elbow_flex': 97, 'wrist_flex': 9, 'wrist_roll': 81}]
        script = """
import {Object3D, Vector3, MathUtils} from './robot_viewer/node_modules/three/build/three.module.js';
import {URDFJoint} from './robot_viewer/node_modules/urdf-loader/src/URDFClasses.js';
let text=''; for await (const c of process.stdin) text+=c;
const {chain,poses}=JSON.parse(text);
const results=poses.map(pose=>{
  const root=new Object3D(); let tip=root;
  for (const spec of chain) {
    const joint=new URDFJoint(); joint.jointType=spec.type; joint.ignoreLimits=true;
    joint.position.fromArray(spec.xyz); joint.rotation.set(...spec.rpy, 'ZYX');
    joint.axis.fromArray(spec.axis); tip.add(joint); tip=joint;
    if(spec.type!=='fixed') joint.setJointValue(MathUtils.degToRad(pose[spec.name]));
  }
  root.updateMatrixWorld(true); return tip.getWorldPosition(new Vector3()).toArray();
}); console.log(JSON.stringify(results));
"""
        result = subprocess.run([node, '--input-type=module', '-e', script], cwd=ROOT, check=True,
                                input=json.dumps({'chain': chain, 'poses': poses}), text=True, capture_output=True)
        for p, xyz in zip(poses, json.loads(result.stdout)):
            self.assertLess(math.dist(forward(p)[0], xyz), 1e-12)


class StoreTests(unittest.TestCase):
    def test_hardware_records_use_calibrated_degree_representation_not_urdf(self):
        position = point(source="hardware", calibration="calibration-A")
        position["pose"]["elbow_flex"] = 97.01098901098901
        self.assertEqual(document(sequence([position]))["points"][0]["pose"], position["pose"])
        position["source"] = "simulation"
        # Offline simulation can also use follower calibration beyond model limits.
        self.assertEqual(document(sequence([position]))["points"][0]["pose"], position["pose"])
        position["pose"]["elbow_flex"] = 181
        with self.assertRaises(ValueError):
            document(sequence([position]))

    def test_atomic_roundtrip_and_revision_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(Path(folder) / "sequences.json")
            doc = store.create(sequence([point()]))
            original = copy.deepcopy(doc)
            doc["name"] = "Renamed"
            changed = store.update(doc["id"], doc, 1)
            self.assertEqual(changed["revision"], 2)
            self.assertEqual(Store(store.path).get(doc["id"]), changed)
            with self.assertRaisesRegex(ValueError, "another tab"):
                store.update(doc["id"], original, 1)
            self.assertEqual(store.get(doc["id"]), changed)
            with patch.object(store, "_flush", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    store.update(doc["id"], original, 2)
            self.assertEqual(store.get(doc["id"]), changed)

    def test_reject_invalid_and_ambiguous_imports(self):
        for bad in ({}, {**sequence(), "units": "radians"}, sequence([point(), point()]), sequence([point(angle=float("nan"))])):
            with self.assertRaises(ValueError):
                document(bad)
        with self.assertRaises(ValueError):
            pose({"shoulder_pan": 0})


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "sequences.json")
        self.clock = Clock()
        self.rt = Runtime(self.store, {}, True, self.clock, FakeHardware)

    def tearDown(self):
        self.rt.close()
        self.temp.cleanup()

    def ready(self, hardware=False, angle=20):
        if hardware:
            self.rt.connect("hardware")
        doc = self.store.create(sequence([point(source=self.rt.mode, calibration=self.rt.device.calibration, angle=angle)]))
        p = self.rt.make_plan(doc["id"], doc["revision"], 20, 60)
        return doc, p

    def cycle(self, dt=1 / 30):
        try:
            self.rt.tick(self.clock.advance(dt))
        except Exception as exc:
            self.rt._fault(str(exc))

    def test_capture_records_measured_follower_during_teleop(self):
        self.rt.connect("hardware")
        doc = self.store.create(sequence())
        self.rt.teleoperate("tab-A")
        self.rt.device.position["shoulder_pan"] = 4.5
        saved = self.rt.record(doc["id"], doc["revision"], "Pickup")
        self.assertEqual(saved["points"][0]["pose"]["shoulder_pan"], 4.5)
        self.assertNotEqual(saved["points"][0]["pose"], self.rt.device.leader())
        self.assertEqual(saved["points"][0]["source"], "hardware")
        self.assertEqual(saved["points"][0]["calibration"], "calibration-A")

    def test_full_plan_execute_without_preview_and_feedback_completion(self):
        _, plan = self.ready(hardware=True)
        self.assertFalse(self.rt.reviewed)
        self.rt.execute(plan["id"], "tab-A")
        for _ in range(400):
            self.rt.heartbeat("tab-A")
            self.cycle()
            if self.rt.activity != "executing":
                break
        self.assertEqual(self.rt.activity, "idle")
        self.assertIn("complete", self.rt.message)
        self.assertAlmostEqual(self.rt.observed["shoulder_pan"], 20)
        self.assertIsNone(self.rt.plan)
        self.assertTrue(self.rt.device.armed)

    def test_edit_reorder_and_start_drift_invalidate_plan(self):
        doc, plan = self.ready()
        self.rt.review(plan["id"])
        self.rt.device.position["shoulder_pan"] += 2
        with self.assertRaisesRegex(ValueError, "planned start"):
            self.rt.execute(plan["id"], "tab-A")
        self.assertIsNone(self.rt.plan)
        plan = self.rt.make_plan(doc["id"], doc["revision"], 20, 60)
        self.rt.review(plan["id"])
        doc["name"] = "New name"
        self.rt.save_sequence(doc["id"], doc, doc["revision"])
        with self.assertRaisesRegex(ValueError, "no longer current"):
            self.rt.execute(plan["id"], "tab-A")

    def test_reject_simulation_or_other_calibration_on_hardware(self):
        self.rt.connect("hardware")
        for source, calibration in (("simulation", None), ("hardware", "other-arm")):
            doc = self.store.create(sequence([point(source=source, calibration=calibration)]))
            with self.assertRaisesRegex(ValueError, "current calibration"):
                self.rt.make_plan(doc["id"], 1, 20, 60)
        self.assertEqual(self.rt.device.commands, [])

    def test_mixed_sequence_hardware_error_names_simulated_step(self):
        self.rt.connect('hardware')
        doc = self.store.create(sequence([point('Position 3'), point('Home', source='hardware', calibration='calibration-A')]))
        with self.assertRaisesRegex(ValueError, 'Simulated positions: Position 3'):
            self.rt.make_plan(doc['id'], 1, 20, 60)
        self.assertEqual(self.rt.device.commands, [])

    def test_pickup_on_fake_follower_without_preview_tracks_step_indices(self):
        self.rt.connect('hardware')
        doc = self.store.create(sequence([
            point('Approach', angle=0, source='hardware', calibration='calibration-A'),
            pickup(), point('Exit', angle=10, source='hardware', calibration='calibration-A')]))
        plan = self.rt.make_plan(doc['id'], 1, 20, 60)
        self.assertEqual(self.rt.device.commands, [])  # Planning never sends motion.
        self.assertFalse(self.rt.reviewed)
        self.rt.execute(plan['id'], 'tab-A')
        seen = set()
        for _ in range(300):
            self.rt.heartbeat('tab-A')
            self.cycle()
            seen.add(self.rt.step)
            if self.rt.activity != 'executing':
                break
        self.assertEqual(seen, {0, 1, 2})
        self.assertEqual(self.rt.activity, 'idle')
        self.assertAlmostEqual(self.rt.observed['shoulder_pan'], 10)

    def test_pickup_can_be_first_and_failed_replan_leaves_no_executable_plan(self):
        self.rt.connect('hardware')
        doc = self.store.create(sequence([pickup()]))
        plan = self.rt.make_plan(doc['id'], 1, 20, 60)
        self.assertEqual(plan['segments'][0]['from'], self.rt.observed)
        self.rt.review(plan['id'])
        self.rt.device.limits = {**LIMITS, 'elbow_flex': (-.1, .1)}
        with self.assertRaisesRegex(ValueError, 'Pickup step'):
            self.rt.make_plan(doc['id'], 1, 20, 60)
        self.assertIsNone(self.rt.plan)
        self.assertFalse(self.rt.reviewed)
        self.assertEqual(self.rt.device.commands, [])

    def test_stop_cancels_motion_and_holds_measured_pose(self):
        _, plan = self.ready(hardware=True)
        self.rt.review(plan["id"])
        self.rt.execute(plan["id"], "tab-A")
        self.cycle()
        self.rt.stop()
        count = len(self.rt.device.commands)
        self.cycle()
        self.assertEqual(self.rt.activity, "idle")
        self.assertEqual(len(self.rt.device.commands), count)
        self.assertEqual(self.rt.device.commands[-1], self.rt.observed)
        self.assertTrue(self.rt.device.armed)

    def test_watchdog_not_renewed_by_another_tab(self):
        self.rt.connect("hardware")
        self.rt.teleoperate("tab-A")
        for _ in range(95):
            self.rt.heartbeat("tab-B")
            self.cycle()
        self.assertEqual(self.rt.activity, "idle")
        self.assertIn("heartbeat lost", self.rt.message)
        self.assertIsNone(self.rt.owner)

    def test_teleop_matches_cli_filter_at_60hz_and_exclusive_ownership(self):
        self.rt.connect("hardware")
        self.rt.teleoperate("tab-A")
        with self.assertRaises(ValueError):
            self.rt.teleoperate("tab-B")
        reference = TargetFilter(tau=.06, deadband=.2, speed=80)
        self.assertEqual(CONTROL_FPS, 60)
        self.assertEqual(self.rt.state()['teleop_settings'], {'tau': .06, 'deadband': .2, 'speed': 80.})
        previous = self.rt.observed['shoulder_pan']
        for i in range(60):
            self.rt.heartbeat("tab-A")
            observation = {f'{j}.pos': v for j, v in self.rt.device.read().items()}
            self.cycle(PERIOD)
            expected = reference.apply({f'{j}.pos': v for j, v in self.rt.device.leader().items()}, observation, self.clock())
            reference.accept(expected)
            for joint in JOINTS:
                self.assertAlmostEqual(self.rt.device.position[joint], expected[f'{joint}.pos'])
            current = self.rt.device.position['shoulder_pan']
            self.assertLessEqual(abs(current - previous), 80 * (1 / 30 if i == 0 else PERIOD) + 1e-9)
            previous = current
        self.assertEqual(self.rt.activity, 'teleop')
        self.assertGreater(previous, 39.)

    def test_teleop_restart_seeds_new_feedback_and_respects_calibrated_limits(self):
        self.rt.connect('hardware')
        self.rt.teleoperate('tab-A')
        self.cycle(PERIOD)
        self.rt.stop()
        self.rt.device.position['shoulder_pan'] = -20.
        self.rt.device.leader_position['shoulder_pan'] = -19.9
        self.rt.teleoperate('tab-A')
        self.cycle(PERIOD)
        self.assertEqual(self.rt.device.position['shoulder_pan'], -20.)
        self.rt.device.leader_position['shoulder_pan'] = 500.
        for _ in range(200):
            self.rt.heartbeat('tab-A')
            self.cycle(PERIOD)
            self.assertLessEqual(self.rt.device.position['shoulder_pan'], self.rt.device.limits['shoulder_pan'][1])
        self.assertEqual(self.rt.activity, 'teleop')

    def test_teleop_tolerates_wrist_lag_and_catches_up_without_playback_fault(self):
        self.rt.connect('hardware')
        self.rt.device.leader_position = {**HOME, 'wrist_flex': 55.}
        self.rt.teleoperate('tab-A')
        gaps = []
        original_send = self.rt.device.send
        def delayed_wrist(target):
            current = self.rt.device.position['wrist_flex']
            gaps.append(abs(target['wrist_flex'] - current))
            self.rt.device.track = False
            original_send(target)
            self.rt.device.position = {**target, 'wrist_flex': current + (target['wrist_flex'] - current) * (1 - math.exp(-PERIOD / .18))}
        with patch.object(self.rt.device, 'send', delayed_wrist):
            for _ in range(180):
                self.rt.heartbeat('tab-A')
                self.cycle(PERIOD)
                self.assertEqual(self.rt.activity, 'teleop', self.rt.error)
        self.assertGreater(max(gaps), 8.)  # Reproduces the old false stop.
        self.assertLessEqual(max(gaps), 20. + 1e-9)
        self.assertAlmostEqual(self.rt.observed['wrist_flex'], 55., delta=.5)

    def test_teleop_target_cannot_run_away_when_follower_lags(self):
        self.rt.connect('hardware')
        self.rt.device.track = False
        self.rt.device.leader_position = {j: 100. if j == 'gripper' else 80. for j in JOINTS}
        self.rt.teleoperate('tab-A')
        for _ in range(240):
            self.rt.heartbeat('tab-A')
            self.cycle(PERIOD)
            self.assertEqual(self.rt.activity, 'teleop', self.rt.error)
            for j in JOINTS:
                self.assertLessEqual(abs(self.rt.last_command[j] - self.rt.observed[j]), TELEOP_RELATIVE_LIMITS[j] + 1e-9)
                self.assertEqual(self.rt.teleop_filter.previous[f'{j}.pos'], self.rt.last_command[j])
        self.assertEqual(set(self.rt.state()['teleop_limited_joints']), set(JOINTS))
        self.assertIn('catching up', self.rt.message)
        # No unbounded filtered target is hidden behind the cap: reversing the
        # leader starts returning immediately, even after seconds of saturation.
        previous = self.rt.last_command.copy()
        self.rt.device.leader_position = {j: 0. if j == 'gripper' else -80. for j in JOINTS}
        self.cycle(PERIOD)
        for j in JOINTS:
            self.assertLess(self.rt.last_command[j], previous[j])
        self.clock.advance(4)
        self.cycle(PERIOD)
        self.assertEqual(self.rt.activity, 'idle')
        self.assertIn('heartbeat lost', self.rt.message)

    def test_teleop_matches_installed_cli_goal_limiter_with_delayed_feedback(self):
        try:
            from lerobot.robots.utils import ensure_safe_goal_position
        except ImportError:
            self.skipTest('LeRobot is required for the independent CLI comparison')
        self.rt.connect('hardware')
        self.rt.device.track = False
        self.rt.teleoperate('tab-A')
        reference = TargetFilter(tau=.06, deadband=.2, speed=80)
        with patch('lerobot.robots.utils.logging.warning'):
            for i in range(360):
                for joint in JOINTS:
                    current = self.rt.device.position[joint]
                    self.rt.device.position[joint] += .05 * (self.rt.last_command[joint] - current)
                    self.rt.device.leader_position[joint] = (50 + 35 * math.sin(i / 25) if joint == 'gripper'
                                                            else 70 * math.sin(i / 25))
                observation = self.rt.device.read()
                self.rt.heartbeat('tab-A')
                self.cycle(PERIOD)
                filtered = reference.apply({f'{j}.pos': v for j, v in self.rt.device.leader().items()},
                                           {f'{j}.pos': v for j, v in observation.items()}, self.clock())
                expected = ensure_safe_goal_position({j: (filtered[f'{j}.pos'], observation[j]) for j in JOINTS}, TELEOP_RELATIVE_LIMITS)
                reference.accept({f'{j}.pos': v for j, v in expected.items()})
                self.assertEqual(self.rt.activity, 'teleop', self.rt.error)
                for joint in JOINTS:
                    self.assertAlmostEqual(self.rt.last_command[joint], expected[joint])

    def test_playback_keeps_strict_wrist_tracking_error(self):
        self.rt.connect('hardware')
        step = point('Wrist target', angle=0, source='hardware', calibration='calibration-A')
        step['pose']['wrist_flex'] = 55.
        doc = self.store.create(sequence([step]))
        plan = self.rt.make_plan(doc['id'], doc['revision'], 20, 60)
        self.rt.review(plan['id'])
        self.rt.execute(plan['id'], 'tab-A')
        self.rt.device.track = False
        for _ in range(300):
            self.rt.heartbeat('tab-A')
            self.cycle(PERIOD)
            if self.rt.activity == 'fault':
                break
        self.assertEqual(self.rt.activity, 'fault')
        self.assertIn('wrist flex is not following', self.rt.error)

    def test_sequence_uses_unfiltered_plan_at_60hz_with_scheduling_jitter(self):
        _, plan = self.ready(hardware=True, angle=60)
        planned = self.rt.plan
        self.rt.review(plan['id'])
        self.rt.execute(plan['id'], 'tab-A')
        elapsed = 0.
        for interval in (PERIOD, .018, .020) * 20:
            self.rt.heartbeat('tab-A')
            self.cycle(interval)
            elapsed += interval
            self.assertAlmostEqual(self.rt.elapsed, elapsed)
            expected, _ = planned.at(elapsed)
            for joint in JOINTS:
                self.assertAlmostEqual(self.rt.device.position[joint], expected[joint])
        self.assertEqual(self.rt.activity, 'executing')
        self.rt.heartbeat('tab-A')
        self.cycle(.1)
        self.assertAlmostEqual(self.rt.elapsed, elapsed + 1 / 30)

    def test_stall_tracking_failure_and_usb_loss_halt(self):
        for failure in ("stall", "tracking", "usb"):
            with self.subTest(failure=failure):
                if self.rt.mode == "hardware":
                    self.rt.connect("simulation")
                _, plan = self.ready(hardware=True, angle=40)
                self.rt.review(plan["id"])
                self.rt.execute(plan["id"], "tab-A")
                if failure == "stall":
                    self.cycle(0.5)
                elif failure == "usb":
                    self.rt.device.fail_read = True
                    self.cycle()
                else:
                    self.rt.device.track = False
                    for _ in range(200):
                        self.rt.heartbeat("tab-A")
                        self.cycle()
                self.assertEqual(self.rt.activity, "fault")
                self.assertIsNone(self.rt.plan)
                self.assertIsNone(self.rt.owner)

    def test_stop_preempts_an_inflight_enable(self):
        _, plan = self.ready(hardware=True)
        self.rt.review(plan["id"])
        entered, finish = threading.Event(), threading.Event()
        original = self.rt.device.enable
        def slow_enable(*args, **kwargs):
            original(*args, **kwargs)
            entered.set()
            finish.wait(2)
        errors = []
        def execute():
            try:
                self.rt.execute(plan["id"], "tab-A")
            except ValueError as exc:
                errors.append(str(exc))
        with patch.object(self.rt.device, "enable", slow_enable):
            worker = threading.Thread(target=execute)
            worker.start()
            self.assertTrue(entered.wait(2))
            stopper = threading.Thread(target=self.rt.stop)
            stopper.start()
            finish.set()
            worker.join(3)
            stopper.join(3)
        self.assertIn("Start cancelled by Stop", errors)
        self.assertNotEqual(self.rt.activity, "executing")

    def check_control_tick_queued_during_start(self, activity):
        """Reproduce the loop waiting behind the API's serial/torque startup."""
        self.rt.connect('hardware')
        if activity == 'executing':
            _, plan = self.ready()
            self.rt.review(plan['id'])
        queued = threading.Event()
        original_lock, original_tick = self.rt.lock, self.rt.tick
        class ObservedLock:
            def __enter__(self):
                if threading.current_thread().name == 'queued-control':
                    queued.set()
                original_lock.acquire()
            def __exit__(self, *args):
                original_lock.release()
        self.rt.lock = ObservedLock()
        def one_tick(now):
            try:
                original_tick(now)
            finally:
                self.rt.shutdown.set()
        with patch.object(self.rt, 'tick', one_tick):
            with self.rt.lock:
                worker = threading.Thread(target=self.rt._loop, name='queued-control')
                worker.start()
                self.assertTrue(queued.wait(1))
                self.clock.advance(.08)  # API startup takes time holding the lock.
                if activity == 'teleop':
                    self.rt.teleoperate('tab-A')
                else:
                    self.rt.execute(plan['id'], 'tab-A')
            worker.join(2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.rt.activity, activity, self.rt.error)
        self.assertIsNone(self.rt.error)

    def test_teleop_start_does_not_fault_when_control_tick_was_waiting_for_lock(self):
        self.check_control_tick_queued_during_start('teleop')

    def test_playback_start_does_not_fault_when_control_tick_was_waiting_for_lock(self):
        self.check_control_tick_queued_during_start('executing')


class APITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.rt = Runtime(Store(Path(self.temp.name) / "db.json"), {})
        self.server = StudioServer(("127.0.0.1", 0), self.rt, ROOT / "robot_viewer/dist")
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.rt.close()
        self.temp.cleanup()

    def request(self, route, data=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        final_headers = {"Content-Type": "application/json", "X-Studio-Token": self.server.token}
        final_headers.update(headers or {})
        connection.request("POST" if data is not None else "GET", route,
                           json.dumps(data) if data is not None else None, final_headers)
        result = connection.getresponse()
        status, body = result.status, json.loads(result.read())
        connection.close()
        return status, body

    def test_origin_host_and_control_token(self):
        self.assertEqual(self.request("/api/stop", {}, {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("/api/stop", {}, {"X-Studio-Token": "wrong"})[0], 403)
        self.assertEqual(self.request("/api/bootstrap", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("/api/connect", {"mode": "hardware"})[0], 400)
        self.assertEqual(self.request("/api/state")[0], 200)

    def test_record_save_plan_execute_without_review_api(self):
        _, boot = self.request("/api/bootstrap")
        doc = boot["sequences"][0]
        status, response = self.request("/api/record", {"sequence_id": doc["id"], "revision": doc["revision"], "name": "Rest"})
        self.assertEqual(status, 200)
        doc = response["sequence"]
        status, response = self.request("/api/plan", {"sequence_id": doc["id"], "revision": doc["revision"], "speed": 20, "acceleration": 60})
        self.assertEqual(status, 200)
        plan_id = response["plan"]["id"]
        self.assertEqual(self.request("/api/execute", {"plan_id": plan_id, "client": "test"})[0], 200)
        self.assertEqual(self.request("/api/stop", {})[1]["state"]["activity"], "idle")


class HardwareAdapterTests(unittest.TestCase):
    def setUp(self):
        try:
            import lerobot.motors.feetech
        except ImportError:
            self.skipTest('Hardware adapter tests require requirements.txt in the local venv')
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = {
            role: {'usb_serial': role + '-usb', 'id': role + '-id', 'port': '/dev/obsolete'}
            for role in ('follower', 'leader')
        }
        for role, folder in (('follower', 'robots'), ('leader', 'teleoperators')):
            path = self.root / folder / ('so_' + role) / (role + '-id.json')
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({j: dict(id=i, drive_mode=0, homing_offset=0, range_min=500, range_max=3500)
                                        for i, j in enumerate(JOINTS, 1)}))
        self.events = []
        events = self.events
        class Bus:
            def __init__(self, port, motors, calibration):
                self.port, self.motors, self.calibration = port, motors, calibration
                self.is_connected = False
                self.is_calibrated = True
                self.port_handler = type('Port', (), {'ser': type('Serial', (), {'exclusive': False})()})()
                events.append(('create', port))
            def connect(self):
                self.is_connected = True
                events.append(('connect', self.port))
            def sync_read(self, register, **kwargs):
                events.append(('read', register))
                return dict.fromkeys(JOINTS, 0) if register == 'Operating_Mode' else HOME.copy()
            def sync_write(self, register, value, **kwargs):
                events.append(('write', register, value.copy()))
            def enable_torque(self, **kwargs):
                events.append(('enable', self.port))
            def disable_torque(self, **kwargs):
                events.append(('release', self.port))
            def disconnect(self, disable_torque=True):
                self.is_connected = False
                events.append(('close', self.port, disable_torque))
        self.patchers = [
            patch('lerobot.motors.feetech.FeetechMotorsBus', Bus),
            patch('lerobot.utils.constants.HF_LEROBOT_CALIBRATION', self.root),
            patch('so101_studio.devices.available_ports', return_value=[{'usb_serial': r + '-usb', 'port': '/dev/' + r} for r in ('follower', 'leader')]),
            patch('so101_studio.devices.port_users', return_value=[]),
        ]
        self.Bus = Bus
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(getattr(self, 'patchers', [])):
            patcher.stop()
        if hasattr(self, 'temp'):
            self.temp.cleanup()

    def test_monitor_connect_and_disconnect_do_not_write_motor_configuration(self):
        from so101_studio.devices import Hardware
        device = Hardware(self.config)
        self.assertIn(('create', '/dev/follower'), self.events)
        self.assertNotIn(('create', '/dev/obsolete'), self.events)
        self.assertFalse(any(e[0] in ('write', 'enable', 'release') for e in self.events))
        device.close()
        self.assertEqual([e[2] for e in self.events if e[0] == 'close'], [False, False])

    def test_busy_leader_is_rejected_before_opening_either_bus(self):
        from so101_studio.devices import Hardware
        with patch('so101_studio.devices.port_users', side_effect=lambda port: [{'pid': 1234, 'process': 'teleoperate'}] if port == '/dev/leader' else []):
            with self.assertRaisesRegex(ValueError, 'detected but busy'):
                Hardware(self.config)
        self.assertEqual(self.events, [])

    def test_calibration_sets_limits_and_accepts_elbow_beyond_nominal_model(self):
        from so101_studio.devices import Hardware
        device = Hardware(self.config)
        expected_half = 3000 * 180 / 4095
        self.assertEqual(device.limits['elbow_flex'], (-expected_half, expected_half))
        observed = {**HOME, 'elbow_flex': 97.01098901098901}
        with patch.object(device.buses['follower'], 'sync_read', return_value=observed):
            self.assertEqual(device.read(), observed)
        with self.assertRaises(ValueError):
            device.send({**HOME, 'elbow_flex': expected_half + 1})
        self.assertFalse(any(e[0] == 'write' for e in self.events))
        device.close()

    def test_inventory_reports_busy_without_opening_serial(self):
        from so101_studio.devices import device_inventory
        with patch('so101_studio.devices.port_users', return_value=[{'pid': -1, 'process': 'teleoperate'}]):
            result = device_inventory(self.config)
        self.assertTrue(result['arms']['follower']['detected'])
        self.assertTrue(result['arms']['follower']['busy'])
        self.assertEqual(self.events, [])

    def test_offline_simulation_plans_records_and_plays_calibrated_mixed_poses(self):
        # Reproduce the reported Home pose with the real shoulder travel width.
        calibration_path = self.root / 'robots/so_follower/follower-id.json'
        calibration = json.loads(calibration_path.read_text())
        calibration['shoulder_lift'].update(range_min=898, range_max=3219)
        calibration_path.write_text(json.dumps(calibration))
        store = Store(self.root / 'offline-sequences.json')
        clock = Clock()
        rt = Runtime(store, self.config, clock=clock)
        try:
            self.assertIn('offline', rt.state()['limits_source'])
            self.assertAlmostEqual(rt.device.limits['shoulder_lift'][0], -102.02197802197803)
            home = point('Home', source='hardware', calibration='saved-follower-profile')
            home['pose']['shoulder_lift'] = -101.31868131868131
            adapter = point('Outside of adapter', source='hardware', calibration='saved-follower-profile')
            adapter['pose']['shoulder_lift'] = -51.91208791208791
            doc = store.create(sequence([point('Position 3'), home, adapter]))
            plan = rt.make_plan(doc['id'], doc['revision'], 20, 60)
            self.assertEqual(plan['segments'][1]['to']['shoulder_lift'], home['pose']['shoulder_lift'])
            rt.review(plan['id'])
            rt.execute(plan['id'], 'preview-tab')
            for _ in range(1200):
                rt.heartbeat('preview-tab')
                rt.tick(clock.advance())
                if rt.activity != 'executing':
                    break
            self.assertEqual(rt.activity, 'idle')
            self.assertEqual(rt.device.read(), adapter['pose'])
            rt.set_simulation(home['pose'])
            saved = rt.record(doc['id'], doc['revision'], 'Virtual Home')
            reloaded = Store(store.path).get(doc['id'])
            self.assertEqual(saved, reloaded)
            self.assertEqual(reloaded['points'][-1]['source'], 'simulation')
            self.assertEqual(self.events, [])  # No serial opens, reads or commands.
        finally:
            rt.close()

    def test_simulation_falls_back_to_model_without_a_calibration_file(self):
        sim = Simulation({'follower': {'id': 'missing-profile'}})
        self.assertEqual(sim.limits, LIMITS)
        self.assertIn('unavailable', sim.limits_source)
        self.assertEqual(self.events, [])

    def test_seed_measured_goal_before_torque_and_release_leader(self):
        from so101_studio.devices import Hardware
        device = Hardware(self.config)
        device.enable(leader=True)
        writes = [e for e in self.events if e[0] == 'write']
        self.assertEqual(writes, [('write', 'Goal_Position', HOME)])
        self.assertLess(self.events.index(writes[0]), self.events.index(('enable', '/dev/follower')))
        self.assertIn(('release', '/dev/leader'), self.events)
        device.close()

    def test_unmatched_identity_missing_calibration_and_mismatch_fail_without_writes(self):
        from so101_studio.devices import Hardware
        config = copy.deepcopy(self.config)
        config['follower']['usb_serial'] = 'wrong-usb'
        with self.assertRaisesRegex(ValueError, 'serial wrong-usb'):
            Hardware(config)
        self.assertEqual(self.events, [])
        with patch('lerobot.utils.constants.HF_LEROBOT_CALIBRATION', self.root / 'missing'):
            with self.assertRaisesRegex(ValueError, 'Missing follower calibration'):
                Hardware(self.config)
        self.assertEqual(self.events, [])
        def mismatched(*args, **kwargs):
            bus = self.Bus(*args, **kwargs)
            bus.is_calibrated = False
            return bus
        with patch('lerobot.motors.feetech.FeetechMotorsBus', side_effect=mismatched):
            with self.assertRaisesRegex(ValueError, 'does not match'):
                Hardware(self.config)
        self.assertFalse(any(e[0] in ('write', 'enable', 'release') for e in self.events))
        self.assertIn(('close', '/dev/follower', False), self.events)


if __name__ == '__main__':
    unittest.main()
