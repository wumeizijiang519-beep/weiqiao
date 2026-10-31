import unittest

import numpy as np
import torch

from critic import TwinQValue
from matched_iql import MatchedIQL
from rl_batches import combine_episodes, training_batch, training_fold
from rl_corpus import episode_arrays
from test_rl_corpus import transition


class RLBatchesTests(unittest.TestCase):
    def corpus(self):
        episodes = []
        for index in range(3):
            features = np.full((2, 4), 1e6 if index == 0 else index, dtype=np.float32)
            episodes.append(episode_arrays([transition(20, [0, 0, 1], True)], features,
                                           episode_id=str(index), physical_group='g' + str(index), fold=index))
        return combine_episodes(episodes)

    def test_scaler_fits_training_only_not_held_outlier(self):
        corpus = self.corpus()
        view = training_fold(corpus, 0)
        np.testing.assert_array_equal(view.scaler.mean, np.full(4, 1.5))
        self.assertEqual(set(view.training_episodes), {'1', '2'})

    def test_held_transition_cannot_be_sampled_for_training(self):
        corpus = self.corpus()
        view = training_fold(corpus, 0)
        with self.assertRaisesRegex(ValueError, 'held-out'):
            training_batch(corpus, view, [0], [1], np.zeros(3, dtype=np.int64), device='cpu')

    def test_actual_length_is_target_only_mask_is_known_plan(self):
        corpus = self.corpus()
        view = training_fold(corpus, 0)
        batch = training_batch(corpus, view, [1, 2], [1, 1], np.asarray([0, 1, 2]), device='cpu')
        self.assertEqual(batch['mask'].sum(1).tolist(), [10, 10])
        self.assertEqual(batch['executed_steps'].tolist(), [3, 3])
        self.assertEqual(batch['observation'].shape, (2, 4))
        self.assertNotIn('success', batch)
        self.assertNotIn('actual_length', batch)

    def test_incomplete_permutation_rejected(self):
        corpus = self.corpus()
        view = training_fold(corpus, 0)
        with self.assertRaisesRegex(ValueError, 'permutation'):
            training_batch(corpus, view, [1], [1], np.asarray([0]), device='cpu')

    def test_assembled_batch_uses_same_td_targets_for_all_controls(self):
        corpus = self.corpus()
        view = training_fold(corpus, 0)
        batch = training_batch(corpus, view, [1, 2], [1, 1], np.asarray([0, 1, 2]), device='cpu')
        learner = MatchedIQL(TwinQValue(4, width=8))
        losses = learner.update(batch)
        torch.testing.assert_close(losses['action']['target'], torch.ones(2))
        for name in ('state_only', 'permutation'):
            torch.testing.assert_close(losses['action']['target'], losses[name]['target'])


if __name__ == '__main__':
    unittest.main()
