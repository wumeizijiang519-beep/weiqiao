"""Simple-WAM scheduler adapter with equal shadow-Q compute for every arm."""

from __future__ import annotations

import torch


class EqualComputeVisualQScheduler:
    """Wrap the official scheduler without changing its inference schedule.

    Every arm computes the frozen visual-Q gradient. Only ``visual_qgf`` feeds
    the guided velocity into the native Euler step; control arms feed the
    original velocity while retaining the same shadow diagnostics and cost.
    """

    def __init__(self, native, frozen_q, state: torch.Tensor, arm: str):
        if arm not in {"candidate0", "uniform_random", "critic_rerank", "visual_qgf"}:
            raise ValueError("unknown online arm")
        self.native, self.frozen_q, self.state, self.arm = native, frozen_q, state.detach(), arm
        self.trace, self.final_sample = [], None

    def __getattr__(self, name):
        return getattr(self.native, name)

    def build_inference_schedule(self, *args, **kwargs):
        timesteps, deltas = self.native.build_inference_schedule(*args, **kwargs)
        self.sigmas = timesteps.detach().float() / float(self.native.num_train_timesteps)
        self.index, self.trace, self.final_sample = 0, [], None
        return timesteps, deltas

    @torch.no_grad()
    def step(self, velocity, delta, sample):
        if self.index >= len(self.sigmas):
            raise RuntimeError("more scheduler steps than frozen schedule")
        sigma = self.sigmas[self.index]
        guided, diagnostics = self.frozen_q.guide_velocity(
            self.state, sample, velocity, sigma
        )
        selected_velocity = guided if self.arm == "visual_qgf" else velocity.detach()
        result = self.native.step(selected_velocity, delta, sample)
        record = dict(diagnostics)
        record.update({
            "sigma": float(sigma),
            "arm": self.arm,
            "shadow_computed": True,
            "guidance_committed": self.arm == "visual_qgf" and bool(diagnostics.get("applied")),
            "native_velocity_sha_equal": bool(torch.equal(selected_velocity, velocity.detach()))
            if self.arm != "visual_qgf" else None,
        })
        self.trace.append(record)
        self.final_sample = result.detach().float().cpu().clone()
        self.index += 1
        return result

