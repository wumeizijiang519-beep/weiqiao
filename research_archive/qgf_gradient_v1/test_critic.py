import unittest
import torch

from critic import IQLLearner, TwinQValue


class TestCritic(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(202640101)
        self.model = TwinQValue(5, horizon=3, action_dim=2, width=16)
        self.observation = torch.randn(4, 5)
        self.action = torch.randn(4, 3, 2)
        self.mask = torch.tensor([[True, True, True], [True, True, False],
                                  [True, False, False], [True, True, True]])

    def test_masked_tail_cannot_change_q_or_gradient(self):
        a = self.action.clone().requires_grad_(True)
        score = self.model.conservative_q(self.observation, a, self.mask)
        gradient, = torch.autograd.grad(score.sum(), a)
        self.assertTrue((gradient[~self.mask] == 0).all())
        changed = self.action.clone()
        changed[~self.mask] = float('nan')
        torch.testing.assert_close(score, self.model.conservative_q(self.observation, changed, self.mask))

    def test_valid_iql_update_changes_only_trainable_parameters(self):
        learner = IQLLearner(self.model)
        before = self.model.q1.first.weight.detach().clone()
        result = learner.update({
            'observation': self.observation, 'next_observation': self.observation + .1,
            'action': self.action, 'mask': self.mask, 'executed_steps': self.mask.sum(1),
            'rewards': torch.zeros(4, 3), 'terminal': torch.tensor([False, True, True, False]),
            'episode_weights': torch.ones(4),
        })
        self.assertTrue(all(torch.isfinite(torch.tensor(x)) for x in result.values()))
        self.assertFalse(torch.equal(before, self.model.q1.first.weight))
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in learner.target.parameters()))

    def test_nonprefix_mask_rejected(self):
        self.mask[0] = torch.tensor([True, False, True])
        with self.assertRaises(ValueError):
            self.model.conservative_q(self.observation, self.action, self.mask)


if __name__ == '__main__':
    unittest.main(verbosity=2)
