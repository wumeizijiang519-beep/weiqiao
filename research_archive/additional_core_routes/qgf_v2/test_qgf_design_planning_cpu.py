"""Numerical validation of planning formulas, not tests of QGF efficacy."""

import math
import unittest

from qgf_design_planning_cpu import binomial_pmf, mcnemar_p, paired_power


class PlanningMathTests(unittest.TestCase):
    def test_binomial_matches_direct_small_n(self):
        for n in range(20):
            for p in (0.01, 0.25, 0.5, 0.9):
                actual = binomial_pmf(n, p)
                expected = [math.comb(n, k) * p ** k * (1-p) ** (n-k) for k in range(n+1)]
                for x, y in zip(actual, expected):
                    self.assertAlmostEqual(x, y, places=13)

    def test_large_pmf_is_normalized(self):
        for p in (0.001, 0.5, 0.999):
            probabilities = binomial_pmf(1200, p)
            self.assertAlmostEqual(math.fsum(probabilities), 1.0, places=13)
            self.assertAlmostEqual(sum(k*p_k for k, p_k in enumerate(probabilities)), 1200*p, places=9)

    def test_edge_cases(self):
        self.assertEqual(binomial_pmf(0, .3), [1.0])
        self.assertEqual(binomial_pmf(2, 0), [1., 0., 0.])
        self.assertEqual(binomial_pmf(2, 1), [0., 0., 1.])
        self.assertEqual(paired_power(30, 0, 0), 0)
        with self.assertRaises(ValueError):
            paired_power(30, .2, .1)

    def test_frozen_count_examples(self):
        self.assertAlmostEqual(mcnemar_p(5, 0), .0625, places=14)
        self.assertAlmostEqual(mcnemar_p(6, 0), .03125, places=14)
        self.assertAlmostEqual(mcnemar_p(5, 2), .453125)
        self.assertEqual(mcnemar_p(0, 0), 1)

    def test_power_against_direct_multinomial(self):
        n, delta, q = 12, .10, .30
        p_plus, p_minus = (q+delta)/2, (q-delta)/2
        expected = 0.
        for plus in range(n+1):
            for minus in range(n-plus+1):
                if plus > minus and mcnemar_p(plus, minus) <= .05:
                    expected += (math.comb(n, plus) * math.comb(n-plus, minus)
                                 * p_plus ** plus * p_minus ** minus
                                 * (1-q) ** (n-plus-minus))
        self.assertAlmostEqual(paired_power(n, delta, q), expected, places=13)

    def test_null_positive_tail_and_all_rescue(self):
        self.assertLessEqual(paired_power(100, 0, .3), .025 + 1e-12)
        self.assertAlmostEqual(paired_power(30, .1, .1),
                               math.fsum(binomial_pmf(30, .1)[6:]), places=13)


if __name__ == '__main__':
    unittest.main()
