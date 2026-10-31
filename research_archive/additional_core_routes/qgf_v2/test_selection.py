import math
import unittest

from selection import SelectionConfig, finite_horizon_returns, select_candidate


class SelectionTests(unittest.TestCase):
    def test_agreed_improvement(self):
        q = [[10, 11], [-10, -9], [50, 51]]
        result = select_candidate(q, [[[0]], [[0.2]]], [1])
        self.assertEqual(result["selected_index"], 1)

    def test_disagreement_abstains(self):
        q = [[0, 1], [0, -1], [0, 1]]
        self.assertEqual(select_candidate(q, [[[0]], [[0.2]]], [1])["selected_index"], 0)

    def test_trust_region(self):
        q = [[0, 10]] * 3
        self.assertEqual(select_candidate(q, [[[0]], [[2]]], [1])["selected_index"], 0)

    def test_invalid_alternative_and_baseline(self):
        q = [[0, math.nan]] * 3
        self.assertEqual(select_candidate(q, [[[0]], [[0.2]]], [1])["selected_index"], 0)
        with self.assertRaises(ValueError):
            select_candidate([[math.nan, 1]] * 3, [[[0]], [[0.2]]], [1])

    def test_tie_keeps_baseline(self):
        self.assertEqual(select_candidate([[1, 1]] * 3, [[[0]], [[0.2]]], [1])["selected_index"], 0)

    def test_finite_horizon_success_signal(self):
        self.assertEqual(finite_horizon_returns([0, 0, 1], [10, 10, 2]), [1, 1, 1])
        self.assertEqual(finite_horizon_returns([0, 0], [10, 2]), [0, 0])
        discounted = finite_horizon_returns([0, 1], [10, 2], gamma_per_step=0.99)
        self.assertAlmostEqual(discounted[0], 0.99 ** 10)

    def test_contract_errors(self):
        with self.assertRaises(ValueError):
            SelectionConfig(uncertainty_weight=-1)
        with self.assertRaises(ValueError):
            finite_horizon_returns([1], [0])
        with self.assertRaises(ValueError):
            select_candidate([[0, 1]] * 3, [[[0]], [[1, 2]]], [1])


if __name__ == "__main__":
    unittest.main()
