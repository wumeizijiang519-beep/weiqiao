import unittest

from causal_signal_v2_metrics import qualify


class CausalSignalV2MetricsTest(unittest.TestCase):
    def row(self, index, family, values, successes=(False,) * 8):
        return {"status": "PAIRED_GROUP_COMPLETE", "episode_id": f"e{index}",
                "family": family, "final_goal_fractions": list(values),
                "goal_fractions_at_16": list(values), "successes": list(successes),
                "successes_at_16": list(successes)}

    def test_dense_gate_requires_two_families(self):
        rows = []
        for index in range(12):
            family = "a" if index < 6 else "b"
            rows.append(self.row(index, family, (0.0, 0.25, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)))
        result = qualify(rows)
        self.assertEqual(result["status"], "CAUSAL_SIGNAL_ADMIT")
        self.assertEqual(result["horizon16"]["dense_passing_families"], ["a", "b"])

    def test_binary_gate(self):
        rows = [self.row(i, "a" if i < 6 else "b", (0,) * 8,
                         (False, True, False, False, False, False, False, False)
                         if i in (0, 1, 6, 7) else (False,) * 8) for i in range(12)]
        self.assertEqual(qualify(rows)["status"], "CAUSAL_SIGNAL_ADMIT")

    def test_incomplete_population_stops(self):
        rows = [self.row(i, "a", (0, 1, 0, 0, 0, 0, 0, 0)) for i in range(11)]
        self.assertEqual(qualify(rows)["status"], "NO_EXTENDED_NATIVE_ACTION_VALUE_SIGNAL")


if __name__ == "__main__":
    unittest.main()
