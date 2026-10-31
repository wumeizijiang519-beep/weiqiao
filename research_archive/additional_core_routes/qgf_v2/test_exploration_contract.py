import unittest
import numpy as np
from exploration_contract import choose_random_candidate, validate_commit


class ExplorationTests(unittest.TestCase):
    def test_fixed_random_selection_and_commit(self):
        actions = np.broadcast_to(np.arange(4, dtype=np.float32)[:, None, None], (4, 10, 16)).copy()
        first, second = np.random.default_rng(202619001), np.random.default_rng(202619001)
        choices = [choose_random_candidate(actions, first) for _ in range(100)]
        self.assertEqual(choices, [choose_random_candidate(actions, second) for _ in range(100)])
        self.assertEqual(set(choices), set(range(4)))
        validate_commit(actions, 2, actions[2])
        with self.assertRaises(AssertionError):
            validate_commit(actions, 2, actions[1])

    def test_reject_nonfinite_or_identical_proposals(self):
        actions = np.zeros((4, 10, 16), np.float32)
        rng = np.random.default_rng(0)
        with self.assertRaises(ValueError):
            choose_random_candidate(actions, rng)
        actions[1, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            choose_random_candidate(actions, rng)
