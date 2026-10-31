import unittest

try:
    from .build_failure_critical_cohort_v1 import choose_boundary
except ImportError:
    from build_failure_critical_cohort_v1 import choose_boundary


class FailureCriticalBoundaryTest(unittest.TestCase):
    def test_selects_farthest_boundary_within_chunk(self):
        self.assertEqual(choose_boundary([10, 10, 10, 5], 3), (1, 25))

    def test_requires_minimum_intervention_span(self):
        self.assertIsNone(choose_boundary([5], 0))

    def test_variable_lengths(self):
        self.assertEqual(choose_boundary([7, 9, 8, 4], 3), (0, 28))


if __name__ == '__main__':
    unittest.main()

