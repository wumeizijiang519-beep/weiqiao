import unittest

from build_progress_binding_draft import family_key, goal_terms, proposed_components


class ProgressBindingDraftTest(unittest.TestCase):
    def test_goal_terms_preserve_order(self):
        text = "(:goal\n (And (Close drawer) (In bowl drawer))\n )\n)"
        self.assertEqual(goal_terms(text), [("Close", "drawer"), ("In", "bowl", "drawer")])

    def test_family_is_fail_closed(self):
        self.assertEqual(family_key("KITCHEN_SCENE4_task"), "KITCHEN_SCENE4")
        with self.assertRaises(RuntimeError):
            family_key("UNKNOWN_task")

    def test_components_are_explicit(self):
        terms = [("On", "mug", "plate"), ("In", "can", "basket")]
        components = proposed_components("test", terms)
        self.assertEqual([row["kind"] for row in components],
                         ["object_target_distance", "object_target_distance"])


if __name__ == "__main__":
    unittest.main()
