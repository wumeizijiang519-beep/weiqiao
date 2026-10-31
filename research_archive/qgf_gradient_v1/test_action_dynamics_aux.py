import unittest

import numpy as np

try:
    from .train_action_dynamics_fold import episode_equal, signed_projection
except ImportError:
    from train_action_dynamics_fold import episode_equal, signed_projection

try:
    from .finalize_action_dynamics_aux import bootstrap_lower
except ImportError:
    from finalize_action_dynamics_aux import bootstrap_lower


class ActionDynamicsAuxTest(unittest.TestCase):
    def test_projection_is_deterministic_and_scaled(self):
        a = signed_projection(11, 7, 123)
        b = signed_projection(11, 7, 123)
        self.assertTrue(np.array_equal(a, b))
        self.assertEqual(a.shape, (11, 7))
        self.assertTrue(np.isfinite(a).all())

    def test_episode_equal_not_transition_equal(self):
        values = np.array([1., 3., 10.])
        ids = np.array(['a', 'a', 'b'])
        self.assertEqual(episode_equal(values, ids), 6.)

    def test_bootstrap_lower_is_deterministic(self):
        values = np.array([1., 2., 3.])
        self.assertEqual(bootstrap_lower(values, 9, 100), bootstrap_lower(values, 9, 100))
        self.assertGreater(bootstrap_lower(values, 9, 100), 0.)


if __name__ == '__main__':
    unittest.main()

