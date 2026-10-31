import unittest

from final_metrics import qualify


def row(episode, family, values16, values32, successes16=None, successes32=None):
    successes16 = successes16 or [False] * 8
    successes32 = successes32 or [False] * 8
    return {"episode_id": episode, "family": family, "branches": [
        {"success_at_16": successes16[i], "success_at_32": successes32[i],
         "progress_at_16": {"value": values16[i]},
         "progress_at_32": {"value": values32[i]}} for i in range(8)]}


class MetricsTests(unittest.TestCase):
    def test_no_range_is_negative(self):
        rows = [row(str(i), "A", [0] * 8, [0] * 8) for i in range(12)]
        self.assertEqual(qualify(rows)["status"], "NO_PROGRESS_PAIRWISE_ACTION_VALUE_SIGNAL")

    def test_two_dense_families_admit(self):
        rows = []
        for i in range(6):
            rows.append(row(f"a{i}", "A", [0, 1] * 4, [0] * 8))
            rows.append(row(f"b{i}", "B", [0, 2] * 4, [0] * 8))
        self.assertEqual(qualify(rows)["status"], "PROGRESS_PAIRWISE_ACTION_VALUE_SIGNAL_ADMIT")


if __name__ == "__main__":
    unittest.main()
