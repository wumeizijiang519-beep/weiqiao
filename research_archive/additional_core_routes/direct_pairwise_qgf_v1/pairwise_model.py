"""Direct within-bank candidate scorers for Direct-Pairwise QGF."""

import torch
from torch import nn


class TemporalActionEncoder(nn.Module):
    def __init__(self, width=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(7, 64, 3, padding=1), nn.SiLU(),
            nn.Conv1d(64, width, 3, padding=1), nn.SiLU(),
        )

    def forward(self, action):
        if action.ndim != 3 or action.shape[1:] != (16, 7):
            raise ValueError("Expected 16x7 action prefix")
        return self.net(action.transpose(1, 2)).mean(-1)


class ConditionalScorer(nn.Module):
    def __init__(self, state_dim, width=128, rank=16):
        super().__init__()
        self.action = TemporalActionEncoder(width)
        self.action_score = nn.Linear(width, 1)
        self.state_gate = nn.Sequential(nn.Linear(state_dim, 64), nn.SiLU(), nn.Linear(64, rank))
        self.action_gate = nn.Linear(width, rank)
        self.scale = rank ** -0.5

    def forward(self, state, action):
        action_hidden = self.action(action)
        interaction = (self.state_gate(state) * self.action_gate(action_hidden)).sum(-1) * self.scale
        return self.action_score(action_hidden).squeeze(-1) + interaction


class ActionOnlyScorer(nn.Module):
    def __init__(self, state_dim, width=128):
        super().__init__()
        self.action = TemporalActionEncoder(width)
        self.head = nn.Linear(width, 1)

    def forward(self, state, action):
        return self.head(self.action(action)).squeeze(-1)


class StateOnlyScorer(nn.Module):
    def __init__(self, state_dim):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(state_dim, 64), nn.SiLU(), nn.Linear(64, 1))

    def forward(self, state, action):
        return self.net(state).squeeze(-1)
