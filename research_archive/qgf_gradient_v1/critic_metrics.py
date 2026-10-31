"""Episode-equal diagnostics and paired physical-group bootstrap, no admission claim."""

import numpy as np


QUALIFICATION_SEEDS = (202640101, 202640102, 202640103)


def episode_mse(predictions, targets, episode_ids):
    predictions, targets = np.asarray(predictions), np.asarray(targets)
    episode_ids = np.asarray(episode_ids)
    if (predictions.ndim != 1 or predictions.shape != targets.shape
            or episode_ids.shape != targets.shape or not len(targets)
            or not np.isfinite(predictions).all() or not np.isfinite(targets).all()):
        raise ValueError('Mismatched or nonfinite held-out predictions/targets')
    errors = (predictions.astype(np.float64) - targets.astype(np.float64)) ** 2
    return {str(episode): float(errors[episode_ids == episode].mean())
            for episode in sorted(set(episode_ids))}


def paired_group_interval(differences, groups, *, bootstrap_seed, draws=10000):
    """Resample groups with all their episodes; never treat seeds as new scenes."""
    differences = np.asarray(differences, dtype=np.float64)
    groups = np.asarray(groups)
    if (differences.ndim != 1 or groups.shape != differences.shape
            or not len(groups) or not np.isfinite(differences).all() or draws < 100):
        raise ValueError('Invalid paired group-bootstrap input')
    unique = sorted(set(groups))
    if len(unique) < 2:
        raise ValueError('At least two physical groups needed for an interval')
    sums = np.asarray([differences[groups == group].sum() for group in unique])
    counts = np.asarray([np.count_nonzero(groups == group) for group in unique])
    rng = np.random.default_rng(bootstrap_seed)
    estimates = np.empty(draws)
    for index in range(draws):
        sampled = rng.integers(0, len(unique), len(unique))
        estimates[index] = sums[sampled].sum() / counts[sampled].sum()
    low, high = np.quantile(estimates, [.025, .975])
    return {'episode_equal_mean_difference': float(differences.mean()),
            'paired_physical_group_percentile95_ci': [float(low), float(high)],
            'physical_groups': len(unique), 'episodes': len(groups),
            'bootstrap_seed': int(bootstrap_seed), 'bootstrap_draws': draws}


def summarize_critic_diagnostics(seed_rows, *, bootstrap_seed, draws=10000):
    """All seeds must contain the same episode-equal held-out error records.

    Input errors must already be evaluated against identical actual logged
    finite returns, not each control's separately fitted Bellman targets.
    This helper does not certify those upstream facts or authorize online use.
    """
    if set(seed_rows) != set(QUALIFICATION_SEEDS):
        raise ValueError('Missing or unregistered critic seed; never select a winner')
    error_keys = ('action_mse', 'state_only_mse', 'permutation_mse', 'action_permuted_mse')
    ordered = []
    for seed in QUALIFICATION_SEEDS:
        rows = sorted(seed_rows[seed], key=lambda row: row['episode_id'])
        ids = [row['episode_id'] for row in rows]
        if not rows or len(ids) != len(set(ids)):
            raise ValueError('Empty or duplicate held-out episode')
        if ordered:
            if [(row['episode_id'], row['physical_group']) for row in rows] != [
                    (row['episode_id'], row['physical_group']) for row in ordered[0]]:
                raise ValueError('Seeds do not share matched held-out episodes/groups')
        for row in rows:
            if any(not np.isfinite(row[key]) or row[key] < 0 for key in error_keys):
                raise ValueError('Invalid episode-equal error')
        ordered.append(rows)
    matrix = np.asarray([[[row[key] for key in error_keys] for row in rows] for rows in ordered])
    by_seed = {}
    for seed, errors in zip(QUALIFICATION_SEEDS, matrix):
        means = errors.mean(0)
        by_seed[str(seed)] = {**dict(zip(error_keys, means.tolist())),
                              'action_better_than_state_only': bool(means[0] < means[1]),
                              'action_better_than_permutation': bool(means[0] < means[2]),
                              'within_model_permutation_error_increase': float(means[3] - means[0])}
    # Average model-seed errors within each episode BEFORE scene-group resampling.
    pooled = matrix.mean(0)
    groups = [row['physical_group'] for row in ordered[0]]
    intervals = {}
    for name, column in [('state_only_minus_action', 1), ('permutation_minus_action', 2),
                         ('action_permuted_minus_action', 3)]:
        intervals[name] = paired_group_interval(pooled[:, column] - pooled[:, 0], groups,
                                                bootstrap_seed=bootstrap_seed, draws=draws)
    return {'scope': 'Offline diagnostics only; not data/critic admission or online efficacy.',
            'per_seed_episode_equal_errors': by_seed, 'paired_group_intervals': intervals,
            'model_seeds_treated_as_independent_scenes': False,
            'confidence_interval_type': 'Marginal95percent intervals, not simultaneous/multiplicity-adjusted',
            'qualification_decision': None}
