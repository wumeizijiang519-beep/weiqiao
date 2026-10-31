"""External RL-token autoencoder; importing it never loads Simple-WAM."""

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class TokenConfig:
    feature_dim: int = 3072
    position_dim: int = 5
    num_tokens: int = 1
    token_dim: int = 2048
    num_heads: int = 8
    num_layers: int = 2

    def __post_init__(self):
        if min(self.feature_dim, self.position_dim, self.num_tokens, self.token_dim, self.num_heads, self.num_layers) < 1:
            raise ValueError("token configuration dimensions must be positive")
        if self.token_dim % self.num_heads:
            raise ValueError("token_dim must be divisible by num_heads")


class CrossAttentionBlock(nn.Module):
    def __init__(self, config: TokenConfig):
        super().__init__()
        width = config.token_dim
        self.query_norm = nn.LayerNorm(width)
        self.context_norm = nn.LayerNorm(width)
        self.attention = nn.MultiheadAttention(width, config.num_heads, dropout=0.0, batch_first=True)
        self.ff_norm = nn.LayerNorm(width)
        self.ff = nn.Sequential(nn.Linear(width, 4 * width), nn.GELU(), nn.Linear(4 * width, width))

    def forward(self, queries, context):
        query = self.query_norm(queries)
        context = self.context_norm(context)
        attended = self.attention(query, context, context, need_weights=False)[0]
        queries = queries + attended
        return queries + self.ff(self.ff_norm(queries))


class TokenAutoencoder(nn.Module):
    def __init__(self, config: TokenConfig):
        super().__init__()
        self.config = config
        width = config.token_dim
        self.feature_norm = nn.LayerNorm(config.feature_dim, elementwise_affine=False)
        self.input_projection = nn.Linear(config.feature_dim, width)
        self.position_projection = nn.Sequential(nn.Linear(config.position_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.queries = nn.Parameter(torch.randn(config.num_tokens, width) * 0.02)
        self.encoder_blocks = nn.ModuleList(CrossAttentionBlock(config) for _ in range(config.num_layers))
        self.output_norm = nn.LayerNorm(width)
        self.decoder_positions = nn.Sequential(nn.Linear(config.position_dim, width), nn.SiLU(), nn.Linear(width, width))
        self.decoder_blocks = nn.ModuleList(CrossAttentionBlock(config) for _ in range(config.num_layers))
        self.output_projection = nn.Linear(width, config.feature_dim)

    def encode(self, features, positions):
        if features.ndim != 3 or features.shape[-1] != self.config.feature_dim:
            raise ValueError("features must be [B,N,feature_dim]")
        if positions.ndim == 2:
            positions = positions.unsqueeze(0).expand(features.shape[0], -1, -1)
        if positions.shape != (*features.shape[:2], self.config.position_dim):
            raise ValueError("positions must be [N,5] or [B,N,5]")
        context = self.input_projection(self.feature_norm(features.float()))
        context = context + self.position_projection(positions.float())
        tokens = self.queries.unsqueeze(0).expand(features.shape[0], -1, -1)
        for block in self.encoder_blocks:
            tokens = block(tokens, context)
        return self.output_norm(tokens)

    def forward(self, features, positions):
        tokens = self.encode(features, positions)
        if positions.ndim == 2:
            positions = positions.unsqueeze(0).expand(features.shape[0], -1, -1)
        queries = self.decoder_positions(positions.float())
        for block in self.decoder_blocks:
            queries = block(queries, tokens)
        return tokens, self.output_projection(queries)


def _critic_mlp(input_dim: int, hidden_dim: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.SiLU(),
        nn.Linear(hidden_dim, hidden_dim), nn.SiLU(), nn.Linear(hidden_dim, 1),
    )


class VisualTwinQ(nn.Module):
    """Twin Q over a frozen visual token, proprioception, and K-step action prefix."""

    def __init__(self, state_dim: int = 2057, action_horizon: int = 10,
                 action_dim: int = 7, hidden_dim: int = 512):
        super().__init__()
        self.state_dim = state_dim
        self.action_horizon = action_horizon
        self.action_dim = action_dim
        inputs = state_dim + action_horizon * action_dim
        self.q1 = _critic_mlp(inputs, hidden_dim)
        self.q2 = _critic_mlp(inputs, hidden_dim)

    def forward(self, state, actions):
        if state.ndim != 2 or state.shape[1] != self.state_dim:
            raise ValueError("state must be [B,state_dim]")
        if actions.shape != (len(state), self.action_horizon, self.action_dim):
            raise ValueError("actions must be [B,K,A]")
        inputs = torch.cat((state.float(), actions.float().flatten(1)), dim=1)
        return torch.stack((self.q1(inputs).squeeze(1), self.q2(inputs).squeeze(1)))
