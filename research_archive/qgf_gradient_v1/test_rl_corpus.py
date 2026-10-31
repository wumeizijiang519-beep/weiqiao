import copy
import unittest

import numpy as np

from rl_corpus import episode_arrays, split_episode_groups


def transition(before, rewards, terminal):
    rewards = np.asarray(rewards, dtype=np.float32)
    bank = np.arange(4 * 32 * 7, dtype=np.float32).reshape(4, 32, 7) / 100
    labels = np.full(4, np.nan)
    labels[1] = rewards.sum(dtype=np.float64)
    return {'remaining_before': before, 'remaining_after': before - len(rewards),
            'actual_length': len(rewards), 'selected_index': 1, 'rewards': rewards,
            'candidate_returns': labels, 'candidates_native': bank,
            'candidates_executed_normalized': bank.copy(), 'executed_actions': bank[1, :len(rewards)].copy(),
            'terminal': terminal, 'environment_done': terminal, 'success': terminal,
            'time_limit': before == len(rewards)}


class RLCorpusTests(unittest.TestCase):
    def build(self, rows, gamma=1.):
        return episode_arrays(rows, np.zeros((len(rows) + 1, 4)), episode_id='e',
                              physical_group='g', fold=0, gamma=gamma)[0]

    def test_discount_uses_actual_environment_steps(self):
        data = self.build([transition(30, [0] * 9 + [1], False), transition(20, [1], True)], gamma=.5)
        np.testing.assert_allclose(data['mc_return'], [3 / 1024, 1])
        np.testing.assert_array_equal(data['remaining_before'], [30, 20])
        np.testing.assert_array_equal(data['mask'].sum(1), [10, 10])

    def test_future_terminal_length_never_changes_current_plan(self):
        short = self.build([transition(20, [0, 0, 1], True)])
        long = self.build([transition(20, [0] * 9 + [1], True)])
        np.testing.assert_array_equal(short['observation'], long['observation'])
        np.testing.assert_array_equal(short['action'], long['action'])
        np.testing.assert_array_equal(short['mask'], long['mask'])
        self.assertTrue(np.isnan(short['rewards'][0, 3:]).all())

    def test_unexecuted_candidate_label_rejected(self):
        row = transition(20, [1], True)
        row['candidate_returns'][0] = 0
        with self.assertRaisesRegex(ValueError, 'Unexecuted'):
            self.build([row])

    def test_nonselected_execution_rejected(self):
        row = transition(20, [1], True)
        row['executed_actions'][0, 0] += 1
        with self.assertRaisesRegex(ValueError, 'Executed prefix'):
            self.build([row])

    def test_missing_or_early_terminal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'terminal'):
            self.build([transition(20, [0] * 10, False)])
        with self.assertRaisesRegex(ValueError, 'terminal'):
            self.build([transition(20, [1], True), transition(19, [1], True)])

    def test_nonterminal_short_execution_is_not_a_completed_macro_action(self):
        with self.assertRaisesRegex(ValueError, 'Nonterminal'):
            self.build([transition(20, [0, 0], False), transition(18, [1], True)])

    def test_group_leakage_and_duplicate_episodes_rejected(self):
        rows = [{'episode_id': 'a', 'physical_group': 'g', 'fold': 0},
                {'episode_id': 'b', 'physical_group': 'h', 'fold': 1}]
        self.assertEqual(split_episode_groups(rows, 0), (['b'], ['a']))
        changed = copy.deepcopy(rows)
        changed[1]['physical_group'] = 'g'
        with self.assertRaisesRegex(ValueError, 'across folds'):
            split_episode_groups(changed, 0)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            split_episode_groups(rows + [rows[0]], 0)


if __name__ == '__main__':
    unittest.main()
