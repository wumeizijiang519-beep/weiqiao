"""Small independent critics for the explicitly labelled fixed-feature baseline."""
import torch
from torch import nn


def network(inputs, width):
    return nn.Sequential(nn.Linear(inputs, width), nn.LayerNorm(width), nn.SiLU(),
                         nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 1))


class Critic(nn.Module):
    def __init__(self, state_dim=701, horizon=10, action_dim=16, width=256, state_only=False):
        super().__init__()
        self.state_only = state_only
        self.heads = nn.ModuleList([network(state_dim + horizon * action_dim, width) for _ in range(2)])
        self.value = network(state_dim, width)

    def q(self, state, action):
        if self.state_only:
            action = torch.zeros_like(action)
        features = torch.cat([state, action.flatten(1)], dim=-1)
        return torch.stack([head(features).squeeze(-1) for head in self.heads])

    def v(self, state):
        return self.value(state).squeeze(-1)
