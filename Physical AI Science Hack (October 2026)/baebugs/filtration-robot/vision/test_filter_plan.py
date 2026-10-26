"""Run from the vision/ folder: python -m unittest test_filter_plan"""
import unittest

from filter_plan import build_plan, fraction_of, plan_coarse, plan_split, plan_target

FILTERS = {"F1": 1.5, "F2": 3, "F3": 5, "F4": 8, "F5": 12}


def objects(*widths):
    return [{"id": i, "width_mm": w} for i, w in enumerate(widths, start=1)]


class FractionTest(unittest.TestCase):
    def test_width_equal_to_hole_is_caught(self):
        self.assertEqual(fraction_of(3.0, [8, 3, 1.5]), 1)

    def test_smaller_than_every_hole_passes_through(self):
        self.assertEqual(fraction_of(1.0, [8, 3, 1.5]), 3)


class SplitTest(unittest.TestCase):
    def test_picks_holes_in_the_gaps(self):
        # three clusters: ~1 mm, ~4 mm, 10 mm; 8/3/1.5 sits furthest from every object
        self.assertEqual(plan_split([1.0, 1.2, 4.0, 4.5, 10.0], FILTERS), ["F4", "F2", "F1"])

    def test_more_groups_beats_wider_gaps(self):
        rig = plan_split([2.0, 4.0, 6.0, 10.0], FILTERS)
        plan = build_plan(objects(2.0, 4.0, 6.0, 10.0), FILTERS, rig, "split")
        self.assertEqual(sum(1 for f in plan["fractions"].values() if f["objects"]), 4)


class TargetTest(unittest.TestCase):
    def test_target_isolated_on_one_shelf(self):
        rig = plan_target(FILTERS, 3, 6)
        self.assertEqual(rig, ["F4", "F2", "F1"])  # F3 (5 mm) would split the 3-6 mm target
        plan = build_plan(objects(2.0, 3.5, 5.5, 9.0), FILTERS, rig, "target", (3, 6))
        self.assertEqual(plan["target"]["shelf"], "middle")
        self.assertEqual(plan["fractions"]["middle"]["objects"], [2, 3])
        self.assertEqual(plan["target"]["caught_range_mm"], [3, 8])

    def test_target_bigger_than_every_hole_has_no_guard(self):
        rig = plan_target(FILTERS, 13, 20)
        self.assertEqual(rig[0], "F5")
        plan = build_plan(objects(15.0), FILTERS, rig, "target", (13, 20))
        self.assertEqual(plan["target"]["shelf"], "top")

    def test_target_finer_than_every_hole_is_impossible(self):
        with self.assertRaises(ValueError):
            plan_target(FILTERS, 1, 2)


class CoarseTest(unittest.TestCase):
    def test_each_type_on_its_own_shelf(self):
        # macaroni 5.3, oval seed 3.8, yellow rice 2.3, tiny seed 1.4
        self.assertEqual(plan_coarse([5.3, 3.8, 2.3, 1.4], FILTERS), ["F3", "F2", "F1"])

    def test_largest_types_separated_first(self):
        # 8/5/3 keeps 9, 6 and 4 apart and lets 2 and 1 share; rigs that merge 9 and 6, or 6 and 4,
        # also make 4 groups but lose on the largest types
        self.assertEqual(plan_coarse([9, 6, 4, 2, 1], FILTERS), ["F4", "F3", "F2"])


if __name__ == "__main__":
    unittest.main()
