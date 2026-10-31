"""Position-aware current-frame features from frozen Simple-WAM video states."""

from dataclasses import dataclass
from typing import Mapping

import torch


@dataclass(frozen=True)
class SimpleWAMFeatureSpec:
    layers: tuple[int, ...]
    spatial_stride: int = 1
    num_views: int = 2

    def __post_init__(self):
        object.__setattr__(self, "layers", tuple(int(v) for v in self.layers))
        if not self.layers or len(set(self.layers)) != len(self.layers):
            raise ValueError("layers must contain distinct indices")
        if self.spatial_stride < 1 or self.num_views < 1:
            raise ValueError("spatial_stride and num_views must be positive")


def _coord(index: int, size: int) -> float:
    return 0.0 if size <= 1 else 2.0 * index / (size - 1) - 1.0


def extract_current_video_features(
    captured: Mapping[int, torch.Tensor],
    grid_size: tuple[int, int, int],
    spec: SimpleWAMFeatureSpec,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Return `[B,N,D]` features and `[N,5]` position coordinates.

    Simple-WAM flattens video tokens in temporal, row, column order. The two
    LIBERO cameras are concatenated along the image width, so camera identity is
    recovered from the spatial column. Only temporal plane zero is exported.
    """
    frames, height, total_width = (int(v) for v in grid_size)
    if min(frames, height, total_width) < 1 or total_width % spec.num_views:
        raise ValueError("invalid Simple-WAM video grid or camera split")
    view_width = total_width // spec.num_views
    parts: list[torch.Tensor] = []
    positions: list[list[float]] = []
    batch = width = None
    for layer_rank, layer in enumerate(spec.layers):
        if layer not in captured:
            raise ValueError(f"missing captured Simple-WAM layer {layer}")
        values = captured[layer]
        if values.ndim != 3 or values.shape[1] != frames * height * total_width:
            raise ValueError("captured video state does not match its grid")
        if batch is None:
            batch, width = values.shape[0], values.shape[2]
        elif values.shape[0] != batch or values.shape[2] != width:
            raise ValueError("captured layers have incompatible shapes")
        indices: list[int] = []
        for view in range(spec.num_views):
            for row in range(0, height, spec.spatial_stride):
                for column in range(0, view_width, spec.spatial_stride):
                    flat_column = view * view_width + column
                    indices.append(row * total_width + flat_column)
                    positions.append([
                        _coord(layer_rank, len(spec.layers)),
                        _coord(view, spec.num_views),
                        0.0,
                        _coord(row, height),
                        _coord(column, view_width),
                    ])
        index = torch.as_tensor(indices, device=values.device, dtype=torch.long)
        parts.append(values.index_select(1, index))
    features = torch.cat(parts, dim=1).detach().float()
    coordinates = torch.tensor(positions, device=features.device, dtype=torch.float32)
    if not torch.isfinite(features).all():
        raise ValueError("captured Simple-WAM features are non-finite")
    return features, coordinates


def prefill_video_cache_with_features(
    mot,
    *,
    video_tokens: torch.Tensor,
    video_freqs: torch.Tensor,
    video_t_mod: torch.Tensor,
    video_context_payload: dict | None,
    video_attention_mask: torch.Tensor,
    capture_layers: set[int],
) -> tuple[list[dict[str, torch.Tensor]], dict[int, torch.Tensor]]:
    """Mirror the official uncompiled video prefill and capture selected states.

    This function deliberately calls the same MoT helpers as
    `prefill_video_cache`; it neither changes model parameters nor introduces an
    action token. Source hashes must pin the corresponding Simple-WAM version.
    """
    if not capture_layers or min(capture_layers) < 0:
        raise ValueError("capture_layers must be nonempty nonnegative indices")
    if video_attention_mask.ndim != 2 or video_attention_mask.shape[0] != video_attention_mask.shape[1]:
        raise ValueError("video_attention_mask must be square")
    if video_attention_mask.shape[0] != video_tokens.shape[1]:
        raise ValueError("video mask/token length mismatch")
    if max(capture_layers) >= mot.num_layers:
        raise ValueError("capture layer exceeds the frozen video expert")

    expert = mot.mixtures["video"]
    values = video_tokens
    cache: list[dict[str, torch.Tensor]] = []
    captured: dict[int, torch.Tensor] = {}
    for layer_idx in range(mot.num_layers):
        block = expert.blocks[layer_idx]
        (
            query,
            key,
            value,
            residual,
            gate_msa,
            shift_mlp,
            scale_mlp,
            gate_mlp,
            checkpointing,
        ) = mot._build_expert_attention_io(
            expert=expert,
            block=block,
            x=values,
            freqs=video_freqs,
            t_mod=video_t_mod,
        )
        mixed = mot._mixed_attention(
            q_cat=query,
            k_cat=key,
            v_cat=value,
            attention_mask=video_attention_mask,
            capture_meta={"phase": "video_prefill", "layer_idx": layer_idx, "step_idx": -1},
        )
        values = mot._apply_post_with_optional_checkpoint(
            block=block,
            residual_x=residual,
            gate_msa=gate_msa,
            shift_mlp=shift_mlp,
            scale_mlp=scale_mlp,
            gate_mlp=gate_mlp,
            use_gradient_checkpointing=checkpointing,
            mixed_slice=mixed,
            context_payload=video_context_payload,
        )
        cache.append({"k": key, "v": value})
        if layer_idx in capture_layers:
            captured[layer_idx] = values.detach()
    return cache, captured
