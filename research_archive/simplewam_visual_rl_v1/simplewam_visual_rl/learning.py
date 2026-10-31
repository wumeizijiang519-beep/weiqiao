"""Leakage-safe macro-transition helpers for Simple-WAM visual RL."""

import torch


def planned_prefix(actions: torch.Tensor, planned_steps: torch.Tensor, horizon: int) -> torch.Tensor:
    """Mask only the prefix length known before execution.

    `planned_steps` is derived from the remaining finite horizon. It must not be
    replaced by the realized terminal length, which is post-action information.
    """
    if actions.ndim != 3 or not 1 <= horizon <= actions.shape[1]:
        raise ValueError("actions must be [B,H,A] and contain the critic horizon")
    if planned_steps.shape != actions.shape[:1] or planned_steps.is_floating_point():
        raise ValueError("planned_steps must be an integer vector")
    if (planned_steps < 1).any() or (planned_steps > horizon).any():
        raise ValueError("planned_steps must lie in [1,K]")
    mask = torch.arange(horizon, device=actions.device)[None] < planned_steps[:, None]
    return actions[:, :horizon] * mask.unsqueeze(-1)


@torch.no_grad()
def chunk_td_target(
    rewards: torch.Tensor,
    actual_steps: torch.Tensor,
    terminated: torch.Tensor,
    next_value: torch.Tensor,
    gamma: float,
) -> torch.Tensor:
    """Use realized length only in the target, never in the current Q input."""
    if rewards.ndim != 2 or not 0 <= gamma <= 1:
        raise ValueError("rewards must be [B,K] and gamma in [0,1]")
    shape = rewards.shape[:1]
    if any(item.shape != shape for item in (actual_steps, terminated, next_value)):
        raise ValueError("transition vectors must match the batch")
    if actual_steps.is_floating_point() or (actual_steps < 1).any() or (actual_steps > rewards.shape[1]).any():
        raise ValueError("actual_steps must lie in [1,K]")
    index = torch.arange(rewards.shape[1], device=rewards.device)
    discount = torch.pow(rewards.new_tensor(gamma), index)
    observed = index[None] < actual_steps[:, None]
    accumulated = (rewards * discount * observed).sum(dim=1)
    bootstrap = torch.pow(rewards.new_tensor(gamma), actual_steps)
    bootstrap = bootstrap * (~terminated.bool()).float() * next_value
    return accumulated + bootstrap
