"""Frozen Simple-WAM visual-token critic shared by reranking and QGF."""

from dataclasses import dataclass
from pathlib import Path

import torch

from .models import TokenAutoencoder, TokenConfig, VisualTwinQ


@dataclass(frozen=True)
class QGFConfig:
    execution_horizon: int = 10
    action_dim: int = 7
    continuous_dims: int = 6
    weight: float = 0.1
    max_grad_norm: float = 1.0
    sigma_min: float = 0.0
    sigma_max: float = 1.0

    def __post_init__(self):
        if not (1 <= self.continuous_dims < self.action_dim):
            raise ValueError("continuous dimensions must exclude the gripper")
        if self.execution_horizon < 1 or self.weight < 0 or self.max_grad_norm <= 0:
            raise ValueError("invalid QGF dimensions or coefficients")
        if not 0 <= self.sigma_min <= self.sigma_max <= 1:
            raise ValueError("invalid sigma interval")


class FrozenVisualQ:
    """One fixed ensemble is used unchanged for candidate scores and Q gradients."""

    def __init__(self, token_checkpoint, critic_checkpoints, device,
                 support_min, support_max, config=QGFConfig()):
        self.device, self.config = torch.device(device), config
        payload = torch.load(token_checkpoint, map_location="cpu", weights_only=False)
        self.encoder = TokenAutoencoder(TokenConfig(**payload["model_config"]))
        self.encoder.load_state_dict(payload["model"], strict=True)
        self.critics = []
        for path in critic_checkpoints:
            checkpoint = torch.load(Path(path), map_location="cpu", weights_only=False)
            critic = VisualTwinQ(hidden_dim=int(checkpoint["settings"]["hidden_dim"]))
            critic.load_state_dict(checkpoint["critic"], strict=True)
            self.critics.append(critic)
        if not self.critics:
            raise ValueError("at least one frozen TwinQ checkpoint is required")
        for module in (self.encoder, *self.critics):
            module.to(self.device).eval().requires_grad_(False)
        self.support_min = torch.as_tensor(support_min, dtype=torch.float32, device=self.device)
        self.support_max = torch.as_tensor(support_max, dtype=torch.float32, device=self.device)
        if self.support_min.shape != (config.action_dim,) or self.support_max.shape != (config.action_dim,):
            raise ValueError("support limits must have one value per action dimension")
        if not torch.isfinite(self.support_min).all() or not torch.all(self.support_min < self.support_max):
            raise ValueError("invalid frozen action support")

    @torch.no_grad()
    def encode(self, features, positions, proprio):
        tokens = self.encoder.encode(features.to(self.device), positions.to(self.device)).squeeze(1)
        proprio = proprio.to(self.device, dtype=torch.float32)
        if proprio.ndim == 1:
            proprio = proprio.unsqueeze(0)
        if proprio.shape != (len(tokens), 9):
            raise ValueError("proprioception must be [B,9]")
        return torch.cat((tokens, proprio), dim=1).detach()

    def in_support(self, actions):
        prefix = actions[:, :self.config.execution_horizon].float()
        return ((prefix >= self.support_min) & (prefix <= self.support_max)).flatten(1).all(1)

    def q(self, state, actions):
        if actions.ndim != 3 or actions.shape[2] != self.config.action_dim:
            raise ValueError("actions must be [B,H,7]")
        count = len(actions)
        if len(state) == 1:
            state = state.expand(count, -1)
        if state.shape != (count, 2057):
            raise ValueError("state/action batch mismatch")
        prefix = actions[:, :self.config.execution_horizon]
        values = [critic(state, prefix).min(0).values for critic in self.critics]
        return torch.stack(values).mean(0)

    @torch.no_grad()
    def rerank(self, state, candidates):
        if candidates.ndim != 3 or len(candidates) < 1:
            raise ValueError("candidate bank must be [N,H,A]")
        supported = self.in_support(candidates)
        if not supported[0]:
            raise ValueError("candidate0 is outside frozen action support")
        scores = self.q(state, candidates).detach()
        scores = scores.masked_fill(~supported, -torch.inf)
        index = int(scores.argmax())
        return candidates[index:index + 1], scores, index

    def guide_velocity(self, state, noisy_actions, base_velocity, sigma):
        cfg = self.config
        if noisy_actions.shape != base_velocity.shape or noisy_actions.ndim != 3:
            raise ValueError("sample and velocity must match [B,H,A]")
        sigma_value = float(torch.as_tensor(sigma))
        if not cfg.sigma_min <= sigma_value <= cfg.sigma_max or cfg.weight == 0:
            return base_velocity.detach(), {"applied": False, "reason": "inactive_sigma"}
        with torch.inference_mode(False), torch.enable_grad(), torch.autocast(
            device_type=noisy_actions.device.type, enabled=False
        ):
            sigma_t = torch.as_tensor(sigma, device=noisy_actions.device, dtype=torch.float32)
            clean = noisy_actions.detach().float() - sigma_t * base_velocity.detach().float()
            prefix = clean[:, :cfg.execution_horizon].clone().requires_grad_(True)
            if not self.in_support(prefix).all():
                return base_velocity.detach(), {"applied": False, "reason": "outside_frozen_support"}
            score = self.q(state.detach(), prefix)
            gradient, = torch.autograd.grad(score.sum(), prefix)
            gradient[:, :, cfg.continuous_dims:] = 0
            raw_norm = gradient.flatten(1).norm(dim=1)
            scale = (cfg.max_grad_norm / raw_norm.clamp_min(1e-12)).clamp_max(1)
            gradient = gradient * scale[:, None, None]
            result = base_velocity.detach().float().clone()
            result[:, :cfg.execution_horizon] -= cfg.weight * gradient
        diagnostics = {
            "applied": True, "score": score.detach().cpu().tolist(),
            "raw_grad_norm": raw_norm.detach().cpu().tolist(),
            "used_grad_norm": gradient.flatten(1).norm(dim=1).detach().cpu().tolist(),
            "suffix_max_error": float((result[:, cfg.execution_horizon:] - base_velocity[:, cfg.execution_horizon:]).abs().max())
            if cfg.execution_horizon < result.shape[1] else 0.0,
            "gripper_max_error": float((result[:, :cfg.execution_horizon, cfg.continuous_dims:]
                                         - base_velocity[:, :cfg.execution_horizon, cfg.continuous_dims:]).abs().max()),
        }
        return result.to(base_velocity.dtype).detach(), diagnostics
