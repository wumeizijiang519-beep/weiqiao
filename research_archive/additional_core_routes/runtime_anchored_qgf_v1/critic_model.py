"""Frozen pretrained action embedding and matched pairwise score head."""

import torch
from torch import nn


class ActionEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.input = nn.Linear(7, 128)
        self.mask = nn.Parameter(torch.zeros(128))
        self.position = nn.Parameter(torch.randn(32, 128) * 0.01)
        layer = nn.TransformerEncoderLayer(128, 4, 256, dropout=0.0,
                                           activation="gelu", batch_first=True,
                                           norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, 3)
        self.output = nn.Linear(128, 7)

    def embed_prefix(self, actions):
        if actions.ndim != 3 or actions.shape[1:] != (16, 7):
            raise ValueError("Invalid action prefix")
        padded = torch.zeros((len(actions), 32, 7), device=actions.device, dtype=actions.dtype)
        padded[:, :16] = actions
        hidden = self.input(padded) + self.position[None, :, :]
        return self.encoder(hidden)[:, :16].mean(1)


class PairwiseScore(nn.Module):
    def __init__(self, state_dim, width=128):
        super().__init__()
        self.state = nn.Sequential(nn.Linear(state_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.action = nn.Sequential(nn.Linear(128, width), nn.SiLU(), nn.Linear(width, width))
        self.head = nn.Sequential(nn.SiLU(), nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 1))

    def forward(self, state, action_embedding):
        return self.head(self.state(state) + self.action(action_embedding)).squeeze(-1)
