import copy
import unittest

import numpy as np
import torch

from features import FoldScaler, pool_features
from training_data import GroupEpisodeSampler, transition_example


class FeatureDataTests(unittest.TestCase):
    def test_only_current_frame_and_official_context_pooling(self):
        latent = torch.ones(1, 3, 1, 8, 16)
        context = torch.tensor([[[2., 4.], [0., 0.]]])
        mask = torch.ones(1, 2, dtype=torch.bool)
        value = pool_features(latent, context, mask, torch.zeros(1, 8), 350)
        self.assertEqual(value.shape, (3 * 32 + 2 + 8 + 1,))
        np.testing.assert_array_equal(value[96:98], [1., 2.])
        self.assertEqual(value[-1], .5)
        with self.assertRaisesRegex(ValueError, 'current frame'):
            pool_features(latent.repeat(1, 1, 2, 1, 1), context, mask, torch.zeros(1, 8), 350)

    def test_validation_outlier_does_not_refit_training_scaler(self):
        scaler = FoldScaler().fit(np.asarray([[0., 2.], [2., 2.]]))
        state = scaler.state()
        scaler.transform(np.asarray([[1e8, -1e8]]))
        np.testing.assert_array_equal(scaler.mean, state['mean'])
        np.testing.assert_array_equal(scaler.scale, state['scale'])

    def test_actual_success_length_cannot_be_an_input_feature(self):
        bank = np.arange(4 * 32 * 7, dtype=np.float32).reshape(4, 32, 7)
        data = {'remaining_before': 50, 'remaining_after': 40, 'actual_length': 10,
                'selected_index': 2, 'candidates_executed_normalized': bank,
                'rewards': np.zeros(10), 'terminal': False}
        normal = transition_example(data, [1, 2], [3, 4], 'episode', 'group', 0)
        early = copy.deepcopy(data)
        early.update(remaining_after=47, actual_length=3, rewards=np.asarray([0, 0, 1]), terminal=True)
        terminal = transition_example(early, [1, 2], [3, 4], 'episode', 'group', 0)
        np.testing.assert_array_equal(normal['action'], terminal['action'])
        np.testing.assert_array_equal(normal['mask'], terminal['mask'])
        self.assertEqual(terminal['executed_steps'], 3)
        self.assertTrue(np.isnan(terminal['rewards'][3:]).all())
        near_end = copy.deepcopy(data)
        near_end.update(remaining_before=3, remaining_after=0, actual_length=3,
                        rewards=np.zeros(3), terminal=True)
        last = transition_example(near_end, [1, 2], [3, 4], 'e', 'g', 0)
        self.assertEqual(last['mask'].sum(), 3)
        self.assertTrue(np.isnan(last['action'][3:]).all())

    def test_group_bootstrap_is_reproducible_and_never_samples_holdout(self):
        episodes = {'a': {'physical_group': 'g1', 'transition_indices': [0, 1]},
                    'b': {'physical_group': 'g1', 'transition_indices': [2]},
                    'c': {'physical_group': 'g2', 'transition_indices': [3, 4]}}
        a, b = GroupEpisodeSampler(episodes, 2), GroupEpisodeSampler(episodes, 2)
        ai, aw = a.sample(50)
        bi, bw = b.sample(50)
        np.testing.assert_array_equal(ai, bi)
        np.testing.assert_array_equal(aw, bw)
        self.assertTrue(set(ai) <= {0, 1, 2, 3, 4})
        self.assertTrue(np.isin(aw, [1, 2]).all())


if __name__ == '__main__':
    unittest.main()
