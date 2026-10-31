import unittest
import numpy as np
import torch
from models import Critic
from learning import calibrated_q_loss
from train_critic import bootstrap_indices, discounted_returns


class TrainingMathTests(unittest.TestCase):
    def test_sparse_partial_chunk_return(self):
        rewards = torch.zeros(2, 10)
        rewards[1, 2] = 1
        steps = torch.tensor([10, 3])
        terminal = torch.tensor([False, True])
        reward, returns = discounted_returns(rewards, steps, terminal, 1.)
        torch.testing.assert_close(reward, torch.tensor([0., 1.]))
        torch.testing.assert_close(returns, torch.ones(2))
        _, returns = discounted_returns(rewards, steps, terminal, .99)
        self.assertAlmostEqual(returns[0].item(), .99 ** 12, places=5)

    def test_bootstrap_preserves_natural_class_counts(self):
        episodes = [{'success': n >= 4} for n in range(32)]
        ids = bootstrap_indices(episodes, np.random.default_rng(0))
        self.assertEqual(len(ids), 32)
        self.assertEqual(sum(not episodes[i]['success'] for i in ids), 4)
        np.testing.assert_array_equal(ids, bootstrap_indices(episodes, np.random.default_rng(0)))

    def test_model_update_finite(self):
        torch.manual_seed(0)
        model = Critic(state_dim=7, horizon=2, action_dim=3, width=16)
        before = model.heads[0][0].weight.detach().clone()
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        q = model.q(torch.randn(4, 7), torch.randn(4, 2, 3))
        loss, _ = calibrated_q_loss(q, torch.zeros(4), torch.ones(4), torch.arange(4), mc_weight=.5)
        loss.backward()
        optimizer.step()
        self.assertTrue(torch.isfinite(loss))
        self.assertFalse(torch.equal(before, model.heads[0][0].weight.detach()))

    def test_state_only_is_action_invariant(self):
        model = Critic(state_dim=7, horizon=2, action_dim=3, width=16, state_only=True)
        states = torch.randn(4, 7)
        torch.testing.assert_close(model.q(states, torch.zeros(4, 2, 3)),
                                   model.q(states, torch.ones(4, 2, 3)))


if __name__ == '__main__':
    unittest.main()
