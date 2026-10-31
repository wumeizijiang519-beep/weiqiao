import unittest

from failure_critical_metrics_v1 import qualify


def row(family, success16, success32, dense16, dense32):
    return {"status": "PAIRED_GROUP_COMPLETE", "family": family,
            "successes_at_16": success16, "successes": success32,
            "goal_fractions_at_16": dense16, "final_goal_fractions": dense32}


class MetricsTest(unittest.TestCase):
    def test_binary_requires_four_groups_and_two_families(self):
        rows = []
        for family in ("a", "b"):
            for _ in range(2):
                rows.append(row(family, [False, True] * 4, [False] * 8,
                                [0.0] * 8, [0.0] * 8))
        rows.extend(row("c", [False] * 8, [False] * 8, [0.0] * 8, [0.0] * 8)
                    for _ in range(8))
        self.assertEqual(qualify(rows)["status"], "FAILURE_CRITICAL_ACTION_VALUE_SIGNAL_ADMIT")

    def test_fewer_than_twelve_cannot_admit(self):
        rows = [row("a", [False, True] * 4, [False] * 8,
                    [0.0, 1.0] * 4, [0.0] * 8) for _ in range(11)]
        self.assertEqual(qualify(rows)["status"], "NO_FAILURE_CRITICAL_ACTION_VALUE_SIGNAL")


if __name__ == "__main__":
    unittest.main()
