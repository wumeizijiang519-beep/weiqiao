import unittest
import torch
from learning import calibrated_q_loss, episode_mean, same_state_pair_loss


class LearningTests(unittest.TestCase):
    def test_long_episode_does_not_dominate(self):
        self.assertAlmostEqual(episode_mean(torch.tensor([0., 2., 2., 2.]),
                                           torch.tensor([0, 1, 1, 1])).item(), 1.)

    def test_target_gradients_detached(self):
        q = torch.zeros(3, 4, requires_grad=True)
        td = torch.ones(4, requires_grad=True)
        mc = torch.ones(4, requires_grad=True)
        loss, _ = calibrated_q_loss(q, td, mc, torch.tensor([0, 0, 1, 1]), mc_weight=.5)
        loss.backward()
        self.assertTrue(torch.isfinite(q.grad).all())
        self.assertIsNone(td.grad)
        self.assertIsNone(mc.grad)

    def test_pair_order_and_ties(self):
        returns = torch.tensor([[0., 1.], [1., 1.]])
        ids = torch.tensor([0, 1])
        good = same_state_pair_loss(torch.tensor([[0., 2.], [100., -100.]]), returns, ids)
        bad = same_state_pair_loss(torch.tensor([[2., 0.], [0., 0.]]), returns, ids)
        self.assertLess(good.item(), bad.item())
        scores = torch.ones(2, 2, requires_grad=True)
        same_state_pair_loss(scores, torch.ones(2, 2), ids).backward()
        self.assertTrue(torch.equal(scores.grad, torch.zeros_like(scores)))

    def test_nonfinite_rejected(self):
        with self.assertRaises(FloatingPointError):
            calibrated_q_loss(torch.tensor([[float('nan')]]), torch.zeros(1),
                              torch.zeros(1), torch.tensor([0]))


if __name__ == '__main__':
    unittest.main()
