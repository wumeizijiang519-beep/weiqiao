import unittest

from boundary_anchored_metrics import qualify


class BoundaryAnchoredMetricsTest(unittest.TestCase):
    def row(self, index, family, values, successes=(False, False, False, False)):
        return {"status": "PAIRED_GROUP_COMPLETE", "episode_id": f"e{index}",
                "family": family, "final_goal_fractions": list(values),
                "successes": list(successes)}

    def test_dense_gate_requires_two_families(self):
        rows = []
        for index in range(12):
            family = "a" if index < 6 else "b"
            rows.append(self.row(index, family, (0.0, 0.25, 0.0, 0.0)))
        result = qualify(rows)
        self.assertEqual(result["status"], "PAIRED_DENSE_CRITIC_SIGNAL_PASS")
        self.assertEqual(result["dense_passing_families"], ["a", "b"])

    def test_binary_gate(self):
        rows = [self.row(i, "a" if i < 6 else "b", (0, 0, 0, 0),
                         (False, True, False, False) if i in (0, 1, 6, 7)
                         else (False, False, False, False)) for i in range(12)]
        self.assertEqual(qualify(rows)["status"], "PAIRED_BINARY_SIGNAL_PASS")

    def test_incomplete_population_stops(self):
        rows = [self.row(i, "a", (0, 1, 0, 0)) for i in range(11)]
        self.assertEqual(qualify(rows)["status"], "NO_PAIRED_ACTION_VALUE_SIGNAL")


if __name__ == "__main__":
    unittest.main()
