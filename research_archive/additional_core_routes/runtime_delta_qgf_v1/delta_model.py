"""Compact raw-action dynamics models for Runtime-Delta QGF."""

import torch
from torch import nn


class TemporalActionEncoder(nn.Module):
    def __init__(self, width=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(7, 64, kernel_size=3, padding=1),
            nn.SiLU(),
            nn.Conv1d(64, width, kernel_size=3, padding=1),
            nn.SiLU(),
        )

    def forward(self, action):
        if action.ndim != 3 or action.shape[1:] != (16, 7):
            raise ValueError("Expected 16x7 action prefix")
        return self.net(action.transpose(1, 2)).mean(-1)


class RuntimeDeltaPredictor(nn.Module):
    def __init__(self, state_dim, width=128):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(state_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.action = TemporalActionEncoder(width)
        self.film = nn.Linear(width, width * 2)
        self.head = nn.Sequential(nn.Linear(width * 3, width), nn.SiLU(), nn.Linear(width, 2))

    def forward(self, state, action):
        state_hidden = self.state(state)
        action_hidden = self.action(action)
        gamma, beta = self.film(state_hidden).chunk(2, dim=-1)
        conditioned = action_hidden * (1.0 + 0.1 * gamma) + 0.1 * beta
        return self.head(torch.cat((state_hidden, conditioned, state_hidden * action_hidden), dim=-1))


class StateOnlyPredictor(nn.Module):
    def __init__(self, state_dim, width=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(state_dim, width), nn.SiLU(), nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 2))

    def forward(self, state, action):
        return self.net(state)


class ActionOnlyPredictor(nn.Module):
    def __init__(self, state_dim, width=128):
        super().__init__()
        self.action = TemporalActionEncoder(width)
        self.head = nn.Sequential(nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 2))

    def forward(self, state, action):
        return self.head(self.action(action))
