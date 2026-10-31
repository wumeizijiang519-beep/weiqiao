import unittest

from progress_metric import family_key, relative_progress


class ProgressMetricTest(unittest.TestCase):
    def test_two_object_distance_progress(self):
        family = "LIVING_ROOM_SCENE2_task"
        boundary = {"distances": [0.2, 0.1], "articulation": None}
        current = {"distances": [0.1, 0.05], "articulation": None}
        result = relative_progress(boundary, current, family)
        self.assertAlmostEqual(result["value"], 0.5)
        self.assertEqual(result["components"], [0.5, 0.5])

    def test_articulation_and_distance_are_equal_weight(self):
        family = "KITCHEN_SCENE4_task"
        boundary = {"distances": [0.2], "articulation": -0.16}
        current = {"distances": [0.1], "articulation": 0.0}
        result = relative_progress(boundary, current, family)
        self.assertAlmostEqual(result["value"], 0.75)

    def test_negative_progress_is_preserved(self):
        family = "LIVING_ROOM_SCENE5_task"
        boundary = {"distances": [0.1, 0.1], "articulation": None}
        current = {"distances": [0.2, 0.2], "articulation": None}
        self.assertEqual(relative_progress(boundary, current, family)["value"], -1.0)

    def test_unknown_family_fails(self):
        with self.assertRaises(RuntimeError):
            family_key("UNKNOWN_task")


if __name__ == "__main__":
    unittest.main()
