"""Experimental MC calibration with episode-balanced objectives."""
import torch
from torch.nn import functional as F


def episode_mean(per_row, episode_ids):
    if per_row.ndim != 1 or episode_ids.shape != per_row.shape or not len(per_row):
        raise ValueError('need nonempty aligned row losses and episode IDs')
    if episode_ids.dtype not in (torch.int32, torch.int64):
        raise ValueError('episode IDs must be integers')
    if not torch.isfinite(per_row).all():
        raise FloatingPointError('nonfinite loss')
    # Complete episodes must be sampled uniformly before rows are subsampled.
    return torch.stack([per_row[episode_ids == key].mean()
                        for key in episode_ids.unique()]).mean()


def calibrated_q_loss(q, td_targets, mc_returns, episode_ids, *, mc_weight=1.0):
    if q.ndim != 2 or q.shape[0] < 1:
        raise ValueError('Q must have shape [heads, rows]')
    if td_targets.shape != q.shape[1:] or mc_returns.shape != td_targets.shape:
        raise ValueError('target shape mismatch')
    if not 0 <= mc_weight <= 1:
        raise ValueError('MC weight must be in [0,1]')
    if not all(torch.isfinite(x).all() for x in (q, td_targets, mc_returns)):
        raise FloatingPointError('nonfinite Q or targets')
    td = F.smooth_l1_loss(q, td_targets.detach().expand_as(q), reduction='none').mean(0)
    mc = F.smooth_l1_loss(q, mc_returns.detach().expand_as(q), reduction='none').mean(0)
    td_loss = episode_mean(td, episode_ids)
    mc_loss = episode_mean(mc, episode_ids)
    return (1 - mc_weight) * td_loss + mc_weight * mc_loss, {
        'td_loss': td_loss.detach(), 'mc_loss': mc_loss.detach()}


def same_state_pair_loss(scores, observed_returns, episode_ids):
    """Measured paired branches only; ties supply no preference supervision.

    Each row contains two actions from the same restored state and matched
    continuation conditions. Arbitrary cross-episode pairs are invalid inputs.
    """
    if scores.ndim != 2 or scores.shape[1] != 2 or observed_returns.shape != scores.shape:
        raise ValueError('paired scores and observed returns must be [rows,2]')
    if episode_ids.shape != scores.shape[:1]:
        raise ValueError('episode ID shape mismatch')
    if not torch.isfinite(scores).all() or not torch.isfinite(observed_returns).all():
        raise FloatingPointError('nonfinite paired values')
    difference = observed_returns.detach()[:, 1] - observed_returns.detach()[:, 0]
    valid = difference != 0
    if not valid.any():
        return scores.sum() * 0
    signed_margin = difference[valid].sign() * (scores[valid, 1] - scores[valid, 0])
    return episode_mean(F.softplus(-signed_margin), episode_ids[valid])
