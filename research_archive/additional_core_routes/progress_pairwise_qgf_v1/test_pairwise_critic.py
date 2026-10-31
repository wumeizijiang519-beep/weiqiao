import unittest

import numpy as np
import torch

from pairwise_corpus import deterministic_folds
from pairwise_model import PairwiseScore, pairwise_loss
from train_pairwise_fold import pair_indices


class PairwiseCriticTests(unittest.TestCase):
    def test_folds_are_group_deterministic(self):
        groups = [{"episode_id": f"e{i}", "family": "a" if i < 4 else "b"} for i in range(8)]
        first = deterministic_folds(groups)
        self.assertEqual(first, deterministic_folds(list(reversed(groups))))
        self.assertEqual(set(first.values()), {0, 1, 2, 3})

    def test_pairs_exclude_ties(self):
        pairs = pair_indices(np.array([0, 0, 0]), np.array([0.0, 0.0, 1.0]))
        self.assertEqual(len(pairs), 2)
        self.assertTrue((pairs[:, 2] == 0).all())

    def test_action_gradient_and_state_only_tie(self):
        model = PairwiseScore(5, width=8)
        state = torch.randn(4, 5)
        left = torch.randn(4, 16, 7, requires_grad=True)
        right = torch.randn(4, 16, 7)
        loss = pairwise_loss(model, state, left, right, torch.ones(4))
        loss.backward()
        self.assertGreater(float(left.grad.abs().sum()), 0)
        zeros = torch.zeros_like(left.detach())
        self.assertTrue(torch.equal(model(state, zeros), model(state, zeros)))


if __name__ == "__main__": unittest.main()
