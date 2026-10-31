"""Independently qualify all nine frozen action-dynamics auxiliary workers."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


SEEDS = (202641201, 202641202, 202641203)
FOLDS = (0, 1, 2)
METRICS = ('action_mse', 'state_only_mse', 'within_bank_mse', 'action_with_alternate_mse')


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def bootstrap_lower(values, seed, draws=10000):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError('Invalid physical-group effect values')
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=np.float64)
    for first in range(0, draws, 1000):
        count = min(1000, draws - first)
        sampled = rng.integers(0, len(values), size=(count, len(values)))
        means[first:first + count] = values[sampled].mean(1)
    return float(np.quantile(means, .025))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reports = {}
    for seed in SEEDS:
        for fold in FOLDS:
            run = args.root / 'runs' / f'qgf_action_dynamics_seed{seed}_fold{fold}_v1'
            path = run / 'REPORT.json'
            if not (run / 'WORKER_COMPLETE').exists() or not path.exists():
                raise RuntimeError(f'Missing complete worker {seed}/{fold}')
            report = json.loads(path.read_text())
            if (report['status'] != 'ACTION_DYNAMICS_AUX_WORKER_COMPLETE_NOT_QUALIFICATION'
                    or report['seed'] != seed or report['held_fold'] != fold
                    or report['updates'] != 5000 or report['causal_signal_v2_read'] is not False):
                raise RuntimeError(f'Worker contract changed {seed}/{fold}')
            reports[(seed, fold)] = report

    seed_results = []
    for seed_index, seed in enumerate(SEEDS):
        episodes = []
        for fold in FOLDS:
            episodes.extend(reports[(seed, fold)]['episode_metrics'])
        names = [row['episode_id'] for row in episodes]
        if len(names) != 288 or len(set(names)) != 288:
            raise RuntimeError(f'Held-fold coverage is not exactly 288 for seed {seed}')
        groups = {}
        for row in episodes:
            if not all(np.isfinite(row[name]) for name in METRICS):
                raise RuntimeError('Nonfinite held metric')
            groups.setdefault(row['physical_group'], []).append(row)
        group_metrics = []
        for group, rows in sorted(groups.items()):
            mean = {name: float(np.mean([row[name] for row in rows])) for name in METRICS}
            group_metrics.append(dict(physical_group=group, **mean,
                state_improvement=mean['state_only_mse'] - mean['action_mse'],
                within_bank_improvement=mean['within_bank_mse'] - mean['action_mse'],
                permutation_sensitivity=mean['action_with_alternate_mse'] - mean['action_mse']))
        effects = ('state_improvement', 'within_bank_improvement', 'permutation_sensitivity')
        means = {name: float(np.mean([row[name] for row in group_metrics])) for name in effects}
        lowers = {name: bootstrap_lower([row[name] for row in group_metrics],
                                        202641301 + 10 * seed_index + i)
                  for i, name in enumerate(effects)}
        passed = all(means[name] > 0 and lowers[name] > 0 for name in effects)
        seed_results.append(dict(seed=seed, physical_groups=len(group_metrics), episodes=288,
            group_equal_effect_mean=means, bootstrap_95_lower=lowers, passed=passed,
            episode_equal_mse={name: float(np.mean([row[name] for row in episodes])) for name in METRICS},
            worker_report_sha256={str(fold): sha(args.root / 'runs' /
                f'qgf_action_dynamics_seed{seed}_fold{fold}_v1' / 'REPORT.json') for fold in FOLDS}))
    passed = all(row['passed'] for row in seed_results)
    result = dict(status=('AUX_ACTION_DYNAMICS_SIGNAL' if passed
                          else 'NO_STABLE_AUX_ACTION_DYNAMICS_SIGNAL'),
        protocol='ACTION_DYNAMICS_AUX_V1', all_three_seeds_passed=passed,
        seeds=seed_results, online_qgf_efficacy=None,
        causal_signal_v2_gate_unchanged=True,
        permitted_use=('separately preregistered paired-critic initialization only after independent V2 admission'
                       if passed else 'none; freeze negative auxiliary diagnostic'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    (args.output.parent / 'RESULT_SHA256').write_text(sha(args.output) + '  ' + args.output.name + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

