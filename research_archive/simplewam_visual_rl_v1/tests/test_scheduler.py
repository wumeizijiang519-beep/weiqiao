import torch

from simplewam_visual_rl.scheduler import EqualComputeVisualQScheduler


class Native:
    num_train_timesteps = 1000

    def build_inference_schedule(self, **kwargs):
        del kwargs
        return torch.tensor([1000.0]), torch.tensor([-1.0])

    def step(self, velocity, delta, sample):
        return sample + float(delta) * velocity


class FrozenQ:
    def __init__(self):
        self.calls = 0

    def guide_velocity(self, state, sample, velocity, sigma):
        del state, sample, sigma
        self.calls += 1
        return velocity - 0.5, {"applied": True, "raw_grad_norm": [1.0]}


def test_controls_compute_shadow_but_commit_native_velocity():
    for arm in ("candidate0", "uniform_random", "critic_rerank"):
        q = FrozenQ()
        wrapper = EqualComputeVisualQScheduler(Native(), q, torch.zeros(1, 2057), arm)
        wrapper.build_inference_schedule()
        result = wrapper.step(torch.ones(1, 32, 7), -1.0, torch.zeros(1, 32, 7))
        assert q.calls == 1
        assert torch.equal(result, -torch.ones_like(result))
        assert wrapper.trace[0]["shadow_computed"] is True
        assert wrapper.trace[0]["guidance_committed"] is False


def test_qgf_commits_guided_velocity_only():
    q = FrozenQ()
    wrapper = EqualComputeVisualQScheduler(Native(), q, torch.zeros(1, 2057), "visual_qgf")
    wrapper.build_inference_schedule()
    result = wrapper.step(torch.ones(1, 32, 7), -1.0, torch.zeros(1, 32, 7))
    assert q.calls == 1
    assert torch.equal(result, torch.full_like(result, -0.5))
    assert wrapper.trace[0]["guidance_committed"] is True

