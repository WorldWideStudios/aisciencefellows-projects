"""Run from the arm/ folder: python -m unittest test_motion"""
import unittest

import cv2
import numpy as np

import motion
from motion import Arm, MissedGrab, MissingPose, PracticeFollower, WrongFilter
from teach import poses_needed, practice_poses, routine


class Recorder(PracticeFollower):
    """Stand-in follower that also keeps every goal it was sent."""

    def __init__(self):
        super().__init__()
        self.sent = []

    def send_action(self, action):
        self.sent.append({k.removesuffix(".pos"): v for k, v in action.items()})
        return super().send_action(action)


def make_arm(grip_on_object=True, camera=None):
    layout = motion.load_layout()
    robot = Recorder()
    robot.object_at = 60.0 if grip_on_object else None
    arm = Arm(robot, layout, practice_poses(layout), realtime=False, log=lambda *_: None, camera=camera)
    arm.photo_dir = None  # don't save test frames
    return arm, robot


def seeing(letter):
    """Stand-in wrist camera: a white frame with that filter's marker in the middle (None: no marker)."""
    frame = np.full((480, 640, 3), 255, np.uint8)
    if letter:
        marker_id = motion.load_filters()["markers"][letter]
        marker = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50), marker_id, 120)
        frame[180:300, 260:380] = marker[..., None]
    return lambda: frame


class PosesTest(unittest.TestCase):
    def test_routines_ask_for_every_slot_and_dump_pose(self):
        names = motion.required_poses(motion.load_layout())
        for name in ["rest", "gripper/open", "gripper/closed", "rig/carry", "storage/carry",
                     "rig/top/front", "rig/top/in", "storage/bottom/in", "dish/grip", "pour/tilt"]:
            self.assertIn(name, names)

    def test_transfer_needs_both_carry_poses(self):
        layout = motion.load_layout()
        needed = poses_needed(layout, motion.transfer_steps(layout, "rig/top", "storage/top"))
        self.assertIn("rig/carry", needed)
        self.assertIn("storage/carry", needed)

    def test_missing_pose_stops_with_a_clear_message(self):
        arm, _ = make_arm()
        del arm.poses["rig/top/in"]
        with self.assertRaisesRegex(MissingPose, "save rig/top/in"):
            arm.run(motion.pick_steps(arm.layout, "rig/top"))


class MoveTest(unittest.TestCase):
    def test_moves_never_exceed_the_speed_and_end_on_target(self):
        arm, robot = make_arm()
        arm.move_to("rig/top/front", "slow")
        limit = arm.layout["speeds"]["slow"] / motion.RATE_HZ
        goals = robot.sent
        for a, b in zip(goals, goals[1:]):
            for j in motion.ARM_JOINTS:
                self.assertLessEqual(abs(b[j] - a[j]), limit * 1.05)
        for j in motion.ARM_JOINTS:
            self.assertAlmostEqual(robot.position[j], arm.poses["rig/top/front"][j])


class RoutineTest(unittest.TestCase):
    def test_turns_between_sides_only_at_the_carry_poses(self):
        arm, _ = make_arm()
        arm.run(motion.transfer_steps(arm.layout, "rig/top", "storage/top"))
        side = lambda name: name.split("/")[0]
        for a, b in zip(arm.visited, arm.visited[1:]):
            if side(a) != side(b):
                self.assertEqual((a, b), ("rig/carry", "storage/carry"))
        self.assertEqual(arm.visited[-1], "storage/carry")

    def test_backs_straight_out_of_a_slot(self):
        arm, _ = make_arm()
        arm.run(motion.pick_steps(arm.layout, "rig/middle"))
        i = arm.visited.index("rig/middle/in")
        self.assertEqual(arm.visited[i - 1:i + 2], ["rig/middle/front", "rig/middle/in", "rig/middle/front"])

    def test_missed_grab_opens_backs_out_and_stops(self):
        arm, robot = make_arm(grip_on_object=False)
        with self.assertRaises(MissedGrab):
            arm.run(motion.transfer_steps(arm.layout, "rig/top", "storage/top"))
        self.assertEqual(arm.visited[-1], "rig/top/front")
        self.assertAlmostEqual(robot.position["gripper"], arm.poses["gripper/open"]["gripper"])
        self.assertNotIn("storage/carry", arm.visited)

    def test_dump_grabs_pours_and_puts_the_dish_back(self):
        arm, _ = make_arm()
        arm.run(motion.dump_steps(arm.layout))
        self.assertLess(arm.visited.index("pour/tilt"), arm.visited.index("dish/grip", 2))
        self.assertEqual(arm.visited[-1], "dish/above")


class MarkerTest(unittest.TestCase):
    def test_scan_notes_every_slot(self):
        views = iter(["A", None, "B", None, "D", None])
        arm, _ = make_arm(camera=lambda: seeing(next(views))())
        arm.run(motion.scan_steps(arm.layout))
        self.assertEqual(arm.inventory["slots"], {"rig/top": "A", "rig/middle": None, "rig/bottom": "B",
                                                  "storage/top": None, "storage/middle": "D", "storage/bottom": None})

    def test_a_filter_is_only_in_one_place(self):
        arm, _ = make_arm(camera=seeing("A"))
        arm.run(motion.pick_steps(arm.layout, "rig/top"))
        arm.run([["look", "storage/top"], ["look", "storage/bottom"]])
        self.assertEqual(arm.inventory, {"slots": {"rig/top": None, "storage/bottom": "A"}, "holding": "?"})

    def test_wrong_filter_stops_in_front_without_grabbing(self):
        arm, robot = make_arm(camera=seeing("B"))
        with self.assertRaisesRegex(WrongFilter, "B \\(F2\\), not A \\(F1\\)"):
            arm.run(motion.pick_steps(arm.layout, "rig/top", "A"))
        self.assertEqual(arm.visited[-1], "rig/top/front")
        self.assertNotIn("rig/top/in", arm.visited)
        self.assertAlmostEqual(robot.position["gripper"], arm.poses["gripper/open"]["gripper"])

    def test_moving_a_filter_updates_the_inventory(self):
        arm, _ = make_arm(camera=seeing("A"))
        arm.run(motion.transfer_steps(arm.layout, "rig/top", "storage/middle", "A"))
        self.assertEqual(arm.inventory, {"slots": {"rig/top": None, "storage/middle": "A"}, "holding": None})

    def test_unreadable_marker_carries_on(self):
        arm, _ = make_arm(camera=seeing(None))
        arm.run(motion.pick_steps(arm.layout, "rig/top", "A"))
        self.assertEqual(arm.inventory["holding"], "?")

    def test_no_camera_skips_the_check(self):
        arm, _ = make_arm()
        arm.run(motion.pick_steps(arm.layout, "rig/top", "A"))
        self.assertIn("rig/top/in", arm.visited)

    def test_filter_can_be_named_by_letter_or_id(self):
        layout = motion.load_layout()
        self.assertEqual(routine(layout, ["pick", "rig/top", "f2"])[3], ["look", "rig/top", "B"])
        self.assertEqual(routine(layout, ["move", "rig/top", "storage/top", "a"])[3], ["look", "rig/top", "A"])
        with self.assertRaises(ValueError):
            routine(layout, ["pick", "rig/top", "F9"])


if __name__ == "__main__":
    unittest.main()
