"""Action-explicit critics over frozen UNITAS world-action representations."""
import torch
from torch import nn


class StateEncoder(nn.Module):
    def __init__(self, state_dim, width=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 512), nn.LayerNorm(512), nn.SiLU(),
            nn.Linear(512, width), nn.LayerNorm(width), nn.SiLU())

    def forward(self, state):
        return self.net(state)


class ActionEncoder(nn.Module):
    def __init__(self, action_dim=16, width=128, horizon=10):
        super().__init__()
        self.step = nn.Sequential(nn.Linear(action_dim, width), nn.LayerNorm(width), nn.SiLU())
        self.position = nn.Parameter(torch.zeros(1, horizon, width))
        layer = nn.TransformerEncoderLayer(
            d_model=width, nhead=4, dim_feedforward=256, dropout=0.,
            activation='gelu', batch_first=True, norm_first=True)
        self.temporal = nn.TransformerEncoder(layer, num_layers=2, enable_nested_tensor=False)
        self.output = nn.Sequential(nn.LayerNorm(width), nn.Linear(width, 256), nn.SiLU())

    def forward(self, action):
        encoded = self.temporal(self.step(action) + self.position[:, :action.shape[1]])
        return self.output(encoded.mean(1))


def head(inputs):
    return nn.Sequential(nn.Linear(inputs, 256), nn.LayerNorm(256), nn.SiLU(),
                         nn.Linear(256, 128), nn.SiLU(), nn.Linear(128, 1))


class LatentActionCritic(nn.Module):
    """Twin Q heads; state-only control uses the identical state encoder and heads."""
    def __init__(self, state_dim=9269, state_only=False):
        super().__init__()
        self.state_only = state_only
        self.state = StateEncoder(state_dim)
        self.action = ActionEncoder()
        self.heads = nn.ModuleList([head(512) for _ in range(2)])
        self.value = head(256)

    def q(self, state, action):
        state_features = self.state(state)
        if self.state_only:
            action_features = torch.zeros_like(state_features)
        else:
            action_features = self.action(action)
        features = torch.cat([state_features, action_features], dim=-1)
        return torch.stack([module(features).squeeze(-1) for module in self.heads])

    def v(self, state):
        return self.value(self.state(state)).squeeze(-1)
