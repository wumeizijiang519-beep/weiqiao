import unittest

import numpy as np

from build_registration import boundary_score, fit_support


class RegistrationTest(unittest.TestCase):
    def test_boundary_score_rewards_gripper_transition(self):
        left = np.zeros((2, 7), dtype=np.float32)
        right = np.zeros((2, 7), dtype=np.float32)
        left[-1, 6] = -1
        right[0, 6] = 1
        self.assertEqual(boundary_score({"executed_actions": left},
                                        {"executed_actions": right}), 1.0)

    def test_support_basis_is_deterministic(self):
        rng = np.random.default_rng(7)
        rows = rng.normal(size=(20, 32 * 6))
        report_a, basis_a = fit_support(rows)
        report_b, basis_b = fit_support(rows)
        self.assertEqual(report_a, report_b)
        np.testing.assert_array_equal(basis_a, basis_b)
        self.assertEqual(basis_a.shape, (3, 32, 6))

    def test_support_basis_rejects_short_input(self):
        with self.assertRaises(RuntimeError):
            fit_support(np.zeros((3, 32 * 6)))


if __name__ == "__main__":
    unittest.main()
