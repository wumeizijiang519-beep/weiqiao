"""Read-only diagnostics on frozen QGF data; no model loading or fitting."""

import hashlib
import json
from math import comb
from pathlib import Path

import numpy as np


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
OUT = ROOT / 'qgf_v2/method_data_review_20261025_v1'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def stats(values):
    values = np.asarray(values, dtype=float)
    return {'min': float(values.min()), 'median': float(np.median(values)),
            'mean': float(values.mean()), 'max': float(values.max())}


def mad(bank):
    bank = bank.astype(np.float64)
    return [float(np.abs(bank[i] - bank[j]).mean())
            for i in range(4) for j in range(i + 1, 4)]


def main():
    OUT.mkdir(exist_ok=False)
    source_records = []

    def record(path):
        source_records.append({'path': str(path), 'sha256': sha(path)})

    v4_path = ROOT / 'qgf_v2/v4_intervention_train32_v1/summary.json'
    record(v4_path)
    v4 = read(v4_path)
    v4_rows = []
    for episode in v4['episodes']:
        path = Path(episode['file'])
        record(path)
        assert source_records[-1]['sha256'] == episode['sha256']
        with np.load(path, allow_pickle=False) as data:
            rewards, lengths = data['rewards'], data['executed_steps']
            terminal = data['finite_horizon_terminal']
            reward = (rewards * (np.arange(rewards.shape[1])[None] < lengths[:, None])).sum(axis=1)
            targets = np.empty_like(reward)
            total = 0.0
            for row in reversed(range(len(reward))):
                total = float(reward[row]) + (0.0 if terminal[row] else total)
                targets[row] = total
            v4_rows.append({'seed': episode['seed'], 'success': episode['success'],
                'replans': len(reward), 'nonzero_chunk_rewards': int(np.count_nonzero(reward)),
                'unique_mc_targets': np.unique(targets).tolist(),
                'mc_equals_episode_outcome': bool(np.all(targets == float(episode['success'])))})

    v5_manifest_path = ROOT / 'qgf_v2/v5_candidate_centered_v1/data/manifest.json'
    v5_result_path = ROOT / 'qgf_v2/v5_candidate_centered_v1/RESULT.json'
    record(v5_manifest_path)
    record(v5_result_path)
    v5_manifest, v5_result = read(v5_manifest_path), read(v5_result_path)
    prevalence = []
    for fold in v5_manifest['folds']:
        train_y = [float(item['success']) for item in fold['train']]
        val_y = np.asarray([float(item['success']) for item in fold['validation']])
        value = float(np.mean(train_y))
        prevalence.append({'fold': fold['fold'], 'train_success_rate': value,
            'validation_successes': int(val_y.sum()), 'validation_failures': int((1-val_y).sum()),
            'constant_train_prevalence_episode_mse': float(((value - val_y) ** 2).mean())})
    v5_comparison = {seed: {kind: values['episode_equal_mse'] for kind, values in conditions.items()}
                     for seed, conditions in v5_result['pooled_by_seed'].items()}

    simple_result_path = ROOT / 'runs/simplewam_intervention_train32_v1_result/DATASET_RESULT.json'
    record(simple_result_path)
    simple = read(simple_result_path)
    simple_rows, full_mad, prefix_mad, executed_mad, ratios = [], [], [], [], []
    observed_reward_values = set()
    for shard in simple['sources']:
        report_path = Path(shard) / 'shard_report.json'
        record(report_path)
        report = read(report_path)
        for episode in report['episodes']:
            directory = Path(shard) / f"episode_{episode['episode_local']}"
            chunk_returns, episode_steps = [], 0
            for row in episode['transitions']:
                path = directory / row['path']
                record(path)
                with np.load(path, allow_pickle=False) as data:
                    bank, rewards = data['candidates'], data['rewards']
                    selected = int(data['selected_index'])
                    executed = data['executed_actions']
                    assert bank.shape == (4, 32, 7) and np.isfinite(bank).all()
                    np.testing.assert_array_equal(executed, bank[selected, :len(executed)])
                    assert np.isfinite(rewards).all()
                    chunk_returns.append(float(rewards.sum()))
                    assert float(data['finite_horizon_return']) == chunk_returns[-1]
                    observed_reward_values.update(float(value) for value in rewards)
                    full, prefix, actual = mad(bank), mad(bank[:, :10]), mad(bank[:, :len(executed)])
                    full_mad.extend(full)
                    prefix_mad.extend(prefix)
                    executed_mad.extend(actual)
                    ratios.append(float(np.mean(prefix) / np.mean(full)))
                    episode_steps += len(executed)
            targets = np.cumsum(np.asarray(chunk_returns)[::-1])[::-1]
            simple_rows.append({'seed': episode['environment_seed'], 'initial_state_index': episode['initial_state_index'],
                'success': episode['success'], 'steps': episode_steps, 'replans': len(chunk_returns),
                'nonzero_chunk_returns': int(np.count_nonzero(chunk_returns)),
                'unique_mc_targets': np.unique(targets).tolist(),
                'mc_equals_episode_outcome': bool(np.all(targets == float(episode['success'])))})

    report = {
        'scope': 'POST_HOC_READ_ONLY_METHOD_REVIEW_NOT_TRAINING_OR_NEW_EFFICACY_RESULT',
        'no_gpu_or_new_episode': True,
        'v4': {'episodes': len(v4_rows), 'successes': sum(r['success'] for r in v4_rows),
            'replans': sum(r['replans'] for r in v4_rows),
            'nonzero_chunk_rewards': sum(r['nonzero_chunk_rewards'] for r in v4_rows),
            'episodes_mc_constant_equal_outcome': sum(r['mc_equals_episode_outcome'] for r in v4_rows),
            'per_episode': v4_rows},
        'v5': {'constant_training_prevalence_control': prevalence,
            'pooled_constant_training_prevalence_mse': float(np.mean([r['constant_train_prevalence_episode_mse'] for r in prevalence])),
            'frozen_pooled_results': v5_comparison,
            'note': 'New constant baseline is post hoc descriptive, with train-fold prevalence only; it does not alter any frozen admission decision.'},
        'simplewam': {'episodes': len(simple_rows), 'successes': sum(r['success'] for r in simple_rows),
            'replans': sum(r['replans'] for r in simple_rows),
            'nonzero_chunk_returns': sum(r['nonzero_chunk_returns'] for r in simple_rows),
            'observed_step_reward_values': sorted(observed_reward_values),
            'episodes_mc_constant_equal_outcome': sum(r['mc_equals_episode_outcome'] for r in simple_rows),
            'full32_pairwise_mad': stats(full_mad), 'prefix10_pairwise_mad': stats(prefix_mad),
            'actually_executed_prefix_pairwise_mad': stats(executed_mad),
            'prefix10_to_full32_mean_mad_ratio_per_boundary': stats(ratios),
            'per_episode': simple_rows,
            'note': 'MAD is in this model native units only; it does not measure reward differences or compare across architectures.'},
        'pilot_gate_math': {
            'all_success_probability_n4_if_true_success_0_8': 0.8 ** 4,
            'all_success_probability_n4_if_true_success_0_9': 0.9 ** 4,
            'at_least_6_failures_in32_if_failure_rate_0_1': sum(comb(32, k)*0.1**k*0.9**(32-k) for k in range(6, 33)),
            'at_least_6_failures_in32_if_failure_rate_0_25': sum(comb(32, k)*0.25**k*0.75**(32-k) for k in range(6, 33)),
            'iid_binomial_one_sided95_failure_upper_bound_zero_of32': 1 - 0.05 ** (1/32),
            'assumptions': 'Illustrations assume iid Bernoulli episodes. Shared tasks, indexed initial states and clustered trajectories limit literal application; no population claim is made.'},
        'sources': source_records,
        'auditor_sha256': sha(Path(__file__)),
    }
    with (OUT / 'READ_ONLY_DIAGNOSTICS.json').open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write('\n')
    brief = {key: {k:v for k,v in report[key].items() if k != 'per_episode'}
             for key in ('v4', 'v5', 'simplewam', 'pilot_gate_math')}
    print(json.dumps(brief, indent=2))
    print('REPORT_SHA256=' + sha(OUT / 'READ_ONLY_DIAGNOSTICS.json'))


if __name__ == '__main__':
    main()
