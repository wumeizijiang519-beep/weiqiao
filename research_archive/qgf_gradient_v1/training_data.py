"""Build decision-time RL inputs without leaking actual future termination."""

import numpy as np


def transition_example(data, observation_features, next_features, episode_id, physical_group, fold):
    remaining = int(data['remaining_before'])
    actual = int(data['actual_length'])
    planned = min(10, remaining)
    selected = int(data['selected_index'])
    if not 1 <= actual <= planned or not 0 <= selected < 4:
        raise ValueError('Invalid actual/planned execution lengths')
    bank = np.asarray(data['candidates_executed_normalized'], dtype=np.float32)
    if bank.shape != (4, 32, 7) or not np.isfinite(bank).all():
        raise ValueError('Invalid actually mapped native candidate bank')
    if int(data['remaining_after']) != remaining - actual:
        raise ValueError('Wrong actual horizon transition')
    mask = np.arange(10) < planned
    rewards = np.full(10, np.nan, dtype=np.float32)
    rewards[:actual] = data['rewards']
    action_bank = np.full((4, 10, 7), np.nan, dtype=np.float32)
    action_bank[:, :planned] = bank[:, :planned]
    observations = [np.asarray(x, dtype=np.float32) for x in (observation_features, next_features)]
    if observations[0].shape != observations[1].shape or observations[0].ndim != 1:
        raise ValueError('Feature dimensions disagree')
    if not all(np.isfinite(x).all() for x in observations):
        raise ValueError('Nonfinite observation feature')
    return {'observation': observations[0], 'next_observation': observations[1],
            'action': action_bank[selected].copy(), 'bank': action_bank,
            'mask': mask, 'rewards': rewards, 'executed_steps': actual,
            'planned_steps': planned, 'terminal': bool(data['terminal']),
            'episode_id': episode_id, 'physical_group': physical_group, 'fold': fold,
            'selected_index': selected}


class GroupEpisodeSampler:
    """Bootstrap physical groups, then sample group/episode/transition.

    Episode-count weights compensate for the group-first proposal when fitting
    an episode-equal objective within the resampled population.
    """

    def __init__(self, episode_rows, bootstrap_seed):
        if not episode_rows:
            raise ValueError('Empty training episodes')
        self.episodes = episode_rows
        groups = {}
        for episode, row in episode_rows.items():
            if not row['transition_indices']:
                continue
            groups.setdefault(row['physical_group'], []).append(episode)
        if not groups:
            raise ValueError('No real transitions in training groups')
        ordered = sorted(groups)
        rng = np.random.default_rng(bootstrap_seed)
        self.bootstrap_groups = [ordered[i] for i in rng.integers(0, len(ordered), len(ordered))]
        self.groups = groups
        self.rng = rng

    def sample(self, batch_size):
        indices, weights = [], []
        for _ in range(batch_size):
            group = self.bootstrap_groups[int(self.rng.integers(len(self.bootstrap_groups)))]
            episodes = self.groups[group]
            episode = episodes[int(self.rng.integers(len(episodes)))]
            rows = self.episodes[episode]['transition_indices']
            indices.append(rows[int(self.rng.integers(len(rows)))])
            weights.append(len(episodes))
        return np.asarray(indices, dtype=np.int64), np.asarray(weights, dtype=np.float32)


def permutation_indices(count, seed):
    # Includes identity with the true randomized1/4probability; no outcome filter.
    return np.random.default_rng(seed).integers(0, 4, count, dtype=np.int64)
