import unittest

import torch

from critic import TwinQValue
from matched_iql import MatchedIQL


class MatchedIQLTests(unittest.TestCase):
    def batch(self):
        rewards = torch.zeros(2, 10)
        rewards[0, 2] = 1
        rewards[0, 3:] = float('nan')
        action = torch.randn(2, 10, 7)
        bank = torch.stack([action, action + 1, action + 2, action + 3], 1)
        return {'observation': torch.randn(2, 5), 'next_observation': torch.randn(2, 5),
                'action': action, 'bank': bank, 'mask': torch.ones(2, 10, dtype=torch.bool),
                'rewards': rewards, 'executed_steps': torch.tensor([3, 10]),
                'remaining_before': torch.tensor([50, 50]), 'terminal': torch.tensor([True, False]),
                'permutation_index': torch.tensor([1, 3]), 'mc_return': torch.tensor([1., 0.]),
                'episode_weights': torch.ones(2)}

    def test_common_td_targets_and_no_future_length_input(self):
        torch.manual_seed(4)
        learner = MatchedIQL(TwinQValue(5, width=8))
        batch = self.batch()
        losses = learner.update(batch)
        self.assertEqual(float(losses['action']['target'][0]), 1.)
        for name in ['state_only', 'permutation']:
            torch.testing.assert_close(losses['action']['target'], losses[name]['target'], rtol=0, atol=0)
        torch.testing.assert_close(losses['mc_action']['target'], batch['mc_return'], rtol=0, atol=0)
        self.assertTrue(all(parameter.grad is None for model in learner.targets.values()
                            for parameter in model.parameters()))
        self.assertTrue(torch.equal(batch['mask'].sum(1), torch.tensor([10, 10])))

    def test_actual_length_as_critic_mask_is_rejected(self):
        learner = MatchedIQL(TwinQValue(5, width=8))
        batch = self.batch()
        batch['mask'][0, 3:] = False
        with self.assertRaisesRegex(ValueError, 'known planned length'):
            learner.update(batch)

    def test_state_only_input_does_not_reveal_selected_action(self):
        batch = self.batch()
        self.assertTrue(torch.equal(MatchedIQL.action_input('state_only', batch),
                                    torch.zeros_like(batch['action'])))


if __name__ == '__main__':
    unittest.main()
