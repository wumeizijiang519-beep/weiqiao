"""Matched pairwise ranking models for action identification."""

import torch
from torch import nn


class PairwiseScore(nn.Module):
    def __init__(self, state_dim: int, action_dim: int = 112, width: int = 128):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(state_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.action = nn.Sequential(nn.Linear(action_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.head = nn.Sequential(nn.SiLU(), nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 1))

    def forward(self, state, action):
        if state.ndim != 2 or action.ndim != 3 or action.shape[1:] != (16, 7):
            raise ValueError("Invalid pairwise critic input")
        if not torch.isfinite(state).all() or not torch.isfinite(action).all():
            raise ValueError("Non-finite pairwise critic input")
        return self.head(self.state(state) + self.action(action.flatten(1))).squeeze(-1)


def pairwise_loss(model, state, left, right, target):
    logits = model(state, left) - model(state, right)
    return torch.nn.functional.binary_cross_entropy_with_logits(logits, target)
