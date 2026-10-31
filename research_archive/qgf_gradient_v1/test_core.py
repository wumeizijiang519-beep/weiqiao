import unittest
import torch

from core import (GuidanceConfig, GuidedScheduler, iql_losses,
                  native_support_basis, q_gradient, semimdp_target)


class Euler:
    num_train_timesteps = 1000

    def build_inference_schedule(self, *args, **kwargs):
        return torch.tensor([500., 250.]), torch.tensor([-.25, -.25])

    def step(self, velocity, delta, sample):
        return sample + velocity * delta


class TestCore(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(702601)
        self.x = torch.randn(1, 4, 3)
        self.v = torch.randn_like(self.x)
        self.critic = lambda a: a[:, :, :2].sum((1, 2))

    def wrapper(self, **kwargs):
        cfg = GuidanceConfig(execution_horizon=2, continuous_dims=2, projected=False, **kwargs)
        out = GuidedScheduler(Euler(), cfg, [self.critic])
        out.build_inference_schedule()
        return out

    def test_weight_zero_exact(self):
        wrap = self.wrapper(weight=0)
        wrap.critics = (lambda a: self.fail("zero weight called critic"),)
        self.assertTrue(torch.equal(wrap.step(self.v, -.25, self.x), self.x - .25 * self.v))

    def test_sign_prefix_gripper_and_no_actor_grad(self):
        wrap = self.wrapper(weight=.5)
        self.v.requires_grad_(True)
        base = self.x - .25 * self.v
        guided = wrap.step(self.v, -.25, self.x)
        self.assertGreater(self.critic(guided[:, :2]).item(), self.critic(base[:, :2]).item())
        self.assertTrue(torch.equal(guided[:, 2:], base[:, 2:]))
        self.assertTrue(torch.equal(guided[:, :, 2], base[:, :, 2]))
        self.assertIsNone(self.v.grad)
        self.assertFalse(guided.requires_grad)

    def test_outer_inference_mode(self):
        with torch.inference_mode():
            wrap = self.wrapper(weight=.3)
            value = wrap.step(self.v, -.25, self.x)
        self.assertTrue(torch.isfinite(value).all())

    def test_projection_rank_and_consensus(self):
        bank = torch.zeros(4, 2, 3)
        bank[:, 0, 0] = torch.arange(4)
        basis = native_support_basis(bank, 2, 2)
        self.assertEqual(tuple(basis.shape), (4, 1))
        grad, agreed = q_gradient(self.x, [self.critic] * 3, 2, 2, basis)
        self.assertTrue(agreed.all())
        self.assertEqual(torch.count_nonzero(grad).item(), 1)
        grad, _ = q_gradient(self.x, [self.critic, lambda a: -self.critic(a)], 2, 2, basis)
        self.assertEqual(torch.count_nonzero(grad).item(), 0)

    def test_identical_bank_abstains(self):
        basis = native_support_basis(torch.zeros(4, 2, 3), 2, 2)
        grad, _ = q_gradient(self.x, [self.critic], 2, 2, basis)
        self.assertEqual(torch.count_nonzero(grad).item(), 0)

    def test_correction_budget(self):
        wrap = self.wrapper(weight=100, correction_rms_budget=.01)
        y = wrap.step(self.v, -.25, self.x)
        wrap.step(self.v, -.25, y)
        self.assertLessEqual(sum(x['correction_rms'] for x in wrap.trace), .010001)

    def test_reject_wrong_schedule_and_shape(self):
        with self.assertRaises(ValueError):
            self.wrapper().step(self.v, .25, self.x)
        with self.assertRaises(ValueError):
            self.wrapper().step(self.v, -.2, self.x)
        with self.assertRaises(ValueError):
            self.wrapper().step(self.v[:, :1], -.25, self.x)

    def test_nonfinite_critic_rejected(self):
        with self.assertRaises(ValueError):
            q_gradient(self.x, [lambda a: a.sum((1, 2)) * float('nan')], 2, 2)

    def test_no_reward_for_unexecuted_tail(self):
        rewards = torch.tensor([[1., 2., float('nan')], [0., 1., 5.]])
        lengths = torch.tensor([2, 3])
        done = torch.tensor([False, True])
        target = semimdp_target(rewards, lengths, done, torch.tensor([4., 100.]), .5)
        torch.testing.assert_close(target, torch.tensor([3., 1.75]))

    def test_full_horizon_terminal_no_bootstrap(self):
        target = semimdp_target(torch.ones(1, 2), torch.tensor([2]), torch.tensor([True]), torch.tensor([99.]))
        self.assertEqual(target.item(), 2.)

    def test_iql_targets_detached(self):
        q = torch.tensor([1., 2.], requires_grad=True)
        v = torch.tensor([0., 0.], requires_grad=True)
        tq = torch.tensor([2., -2.], requires_grad=True)
        td = torch.tensor([3., 3.], requires_grad=True)
        qloss, vloss = iql_losses(q, q, v, tq, td, torch.ones(2))
        (qloss + vloss).backward()
        self.assertIsNone(tq.grad)
        self.assertIsNone(td.grad)
        self.assertIsNotNone(q.grad)
        self.assertIsNotNone(v.grad)

    def test_state_only_has_no_action_gradient(self):
        with self.assertRaises(RuntimeError):
            q_gradient(self.x, [lambda a: torch.ones(a.shape[0])], 2, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
