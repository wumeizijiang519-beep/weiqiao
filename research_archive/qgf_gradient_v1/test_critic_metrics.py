import copy
import unittest

import numpy as np

from critic_metrics import QUALIFICATION_SEEDS, episode_mse, paired_group_interval, summarize_critic_diagnostics


class CriticMetricTests(unittest.TestCase):
    def rows(self):
        return {seed: [{'episode_id': f'e{i}', 'physical_group': str(i // 2),
                       'action_mse': .1, 'state_only_mse': .3,
                       'permutation_mse': .2, 'action_permuted_mse': .4}
                      for i in range(8)] for seed in QUALIFICATION_SEEDS}

    def test_long_episode_does_not_gain_more_weight(self):
        errors = episode_mse([1, 1, 1, 0], [0, 0, 0, 0], ['a', 'a', 'a', 'b'])
        self.assertEqual(np.mean(list(errors.values())), .5)

    def test_model_seeds_do_not_triple_number_of_scenes(self):
        result = summarize_critic_diagnostics(self.rows(), bootstrap_seed=9, draws=100)
        interval = result['paired_group_intervals']['state_only_minus_action']
        self.assertEqual(interval['episodes'], 8)
        self.assertEqual(interval['physical_groups'], 4)
        np.testing.assert_allclose(interval['paired_physical_group_percentile95_ci'], [.2, .2])
        self.assertIsNone(result['qualification_decision'])

    def test_bad_seed_cannot_be_dropped(self):
        rows = self.rows()
        del rows[QUALIFICATION_SEEDS[0]]
        with self.assertRaisesRegex(ValueError, 'seed'):
            summarize_critic_diagnostics(rows, bootstrap_seed=3, draws=100)

    def test_mismatched_episode_group_rejected(self):
        rows = self.rows()
        rows[QUALIFICATION_SEEDS[1]][0]['physical_group'] = 'replacement'
        with self.assertRaisesRegex(ValueError, 'matched'):
            summarize_critic_diagnostics(rows, bootstrap_seed=3, draws=100)

    def test_paired_bootstrap_reproducible(self):
        kwargs = {'bootstrap_seed': 31, 'draws': 300}
        a = paired_group_interval([1, 0, -1], ['a', 'a', 'b'], **kwargs)
        b = paired_group_interval([1, 0, -1], ['a', 'a', 'b'], **kwargs)
        self.assertEqual(a, b)

    def test_nonfinite_errors_rejected(self):
        rows = copy.deepcopy(self.rows())
        rows[QUALIFICATION_SEEDS[0]][0]['action_mse'] = np.nan
        with self.assertRaisesRegex(ValueError, 'Invalid'):
            summarize_critic_diagnostics(rows, bootstrap_seed=3, draws=100)


if __name__ == '__main__':
    unittest.main()
