"""Explicit fold-isolated batching for a future admitted critic corpus, no fitting."""

from dataclasses import dataclass

import numpy as np
import torch

from features import FoldScaler
from rl_corpus import split_episode_groups


ARRAY_KEYS = ('observation', 'next_observation', 'action', 'bank', 'mask', 'rewards',
              'executed_steps', 'planned_steps', 'remaining_before', 'selected_index',
              'terminal', 'mc_return')


def combine_episodes(episodes):
    if not episodes:
        raise ValueError('Empty admitted corpus')
    parts, metadata, seen = [], {}, set()
    offset = 0
    dimension = None
    for arrays, meta in episodes:
        name = meta['episode_id']
        if name in seen:
            raise ValueError('Duplicate episode cannot enter fitting twice')
        seen.add(name)
        count = int(meta['transitions'])
        if count < 1 or any(len(arrays[key]) != count for key in ARRAY_KEYS):
            raise ValueError('Incomplete episode arrays')
        shape = arrays['observation'].shape
        if len(shape) != 2 or arrays['next_observation'].shape != shape:
            raise ValueError('Current/next feature matrix mismatch')
        if dimension is not None and shape[1] != dimension:
            raise ValueError('Feature dimension changed across episodes')
        dimension = shape[1]
        metadata[name] = {**meta, 'transition_indices': list(range(offset, offset + count))}
        parts.append(arrays)
        offset += count
    corpus = {key: np.concatenate([part[key] for part in parts]) for key in ARRAY_KEYS}
    corpus['episodes'] = metadata
    return corpus


@dataclass
class TrainingFold:
    held_fold: int
    training_indices: np.ndarray
    held_indices: np.ndarray
    training_episodes: dict
    scaler: FoldScaler


def training_fold(corpus, held_fold):
    metadata = list(corpus['episodes'].values())
    train_ids, held_ids = split_episode_groups(metadata, held_fold)
    train = {name: corpus['episodes'][name] for name in train_ids}
    train_indices = np.asarray([i for name in train_ids for i in train[name]['transition_indices']], dtype=np.int64)
    held_indices = np.asarray([i for name in held_ids for i in corpus['episodes'][name]['transition_indices']], dtype=np.int64)
    if set(train_indices) & set(held_indices):
        raise ValueError('Training/held transition overlap')
    scaler = FoldScaler().fit(corpus['observation'][train_indices])
    return TrainingFold(held_fold, train_indices, held_indices, train, scaler)


def training_batch(corpus, fold, indices, episode_weights, permutation_index, *, device):
    indices = np.asarray(indices)
    weights = np.asarray(episode_weights, dtype=np.float32)
    permutation_index = np.asarray(permutation_index)
    if (indices.ndim != 1 or not len(indices) or not np.issubdtype(indices.dtype, np.integer)
            or not np.isin(indices, fold.training_indices).all()):
        raise ValueError('Batch contains nontraining/held-out transitions')
    if weights.shape != indices.shape or not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError('Invalid episode-equal importance weights')
    if (permutation_index.shape != (len(corpus['action']),)
            or not np.issubdtype(permutation_index.dtype, np.integer)
            or (permutation_index < 0).any() or (permutation_index >= 4).any()):
        raise ValueError('Unregistered or incomplete within-bank permutation')
    # Only these explicit tensors reach MatchedIQL; metadata/future outcomes are
    # not concatenated into current observation features.
    batch = {}
    for key in ('observation', 'next_observation'):
        values = fold.scaler.transform(corpus[key][indices])
        batch[key] = torch.as_tensor(values, device=device, dtype=torch.float32)
    for key in ('action', 'bank', 'rewards', 'mc_return'):
        batch[key] = torch.as_tensor(corpus[key][indices], device=device, dtype=torch.float32)
    for key in ('executed_steps', 'remaining_before'):
        batch[key] = torch.as_tensor(corpus[key][indices], device=device, dtype=torch.int64)
    for key in ('mask', 'terminal'):
        batch[key] = torch.as_tensor(corpus[key][indices], device=device, dtype=torch.bool)
    batch['episode_weights'] = torch.as_tensor(weights, device=device)
    batch['permutation_index'] = torch.as_tensor(permutation_index[indices], device=device, dtype=torch.int64)
    return batch
