"""Final-step diagnostics; not a claim of robotic efficacy or causal ranking."""
import hashlib
import json
from pathlib import Path
import statistics
from cv_conditions import conditions


def main():
    suite = Path(__file__).resolve().parent / 'small_data_cv_v1'
    rows = []
    for condition in conditions():
        directory = suite / 'training' / condition['name']
        if not (directory / 'COMPLETE').exists():
            raise ValueError('all36 fixed runs must finish before the primary report')
        metrics = [json.loads(line) for line in (directory / 'metrics.jsonl').read_text().splitlines()]
        final = metrics[-1]
        if final['step'] != 10000:
            raise ValueError('primary report must use fixed final step')
        rows.append({**condition, 'final': final,
                     'checkpoint_sha256': hashlib.sha256((directory / 'latest.pt').read_bytes()).hexdigest()})
    aggregate = {}
    for kind in ('td099', 'calibrated1', 'state_only'):
        selected = [r for r in rows if r['kind'] == kind]
        per_seed = []
        for seed in range(3):
            folds = [r for r in selected if r['seed'] == seed]
            episodes = [e for r in folds for e in r['final']['per_episode']]
            if len(episodes) != 60 or len({e['seed'] for e in episodes}) != 60:
                raise ValueError('OOF coverage failure')
            per_seed.append({'seed': seed,
                'matched_mc_mse': statistics.mean(e['matched_mc_mse'] for e in episodes),
                'common_success_mse': statistics.mean(e['undiscounted_success_mse'] for e in episodes),
                'success_common_mse': statistics.mean(e['undiscounted_success_mse'] for e in episodes if e['success']),
                'failure_common_mse': statistics.mean(e['undiscounted_success_mse'] for e in episodes if not e['success']),
                'action_shuffle_abs_delta': statistics.mean(r['final']['action_shuffle_abs_delta'] for r in folds)})
        aggregate[kind] = per_seed
    wins = sum(a['common_success_mse'] < b['common_success_mse']
               for a, b in zip(aggregate['calibrated1'], aggregate['state_only']))
    delta = statistics.mean(r['action_shuffle_abs_delta'] for r in aggregate['calibrated1'])
    status = 'DIRECTIONAL_SIGNAL_NEEDS_ONLINE_TEST' if wins == 3 and delta > 1e-4 else 'NO_CONVINCING_ACTION_VALUE_EVIDENCE_IN_THIS_DIAGNOSTIC'
    result = {'diagnostic_only': True, 'status': status, 'independent_episodes': 60,
              'independent_failures': 4, 'aggregate': aggregate, 'runs': rows,
              'warning': 'CV seed repeats/chunks are not independent robot episodes; no online QGF gain demonstrated'}
    (suite / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# Small-data Method Conclusion', '', f'Status: {status}', '',
             'All36 runs evaluated at fixed final10000steps, not validation-selected best.',
             f'Calibrated critic beats same-target state-only common MSE in {wins}/3 seed aggregates.',
             f'Mean calibrated action-shuffle delta: {delta:.8g}.', '',
             '| Method | Seed | Matched MC MSE | Common success MSE | Failure MSE | Shuffle delta |',
             '| --- | --- | --- | --- | --- | --- |']
    for kind, records in aggregate.items():
        for row in records:
            lines.append(f"| {kind} | {row['seed']} | {row['matched_mc_mse']:.6g} | {row['common_success_mse']:.6g} | {row['failure_common_mse']:.6g} | {row['action_shuffle_abs_delta']:.6g} |")
    lines += ['', 'Only four independent failures; uncertainty is substantial. This cannot establish',
              'causal same-state action ranking, general QGF failure/success or robotic gains.',
              'Different discounts imply different target scales; common-target TD error is not',
              'a fair standalone measure of ranking quality. State-only comparison shares gamma1.',
              'Nonzero shuffle response is action dependence, not correct action ordering.',
              'Any online feasibility must use fresh seeds and a separately frozen budget.',
              'No parameter/fold selection or additional collection follows automatically.']
    (suite / 'METHOD_CONCLUSION.md').write_text('\n'.join(lines) + '\n')
    (suite / 'COMPLETE').touch()
    print(json.dumps({'status': status, 'calibrated_vs_state_only_wins': wins, 'shuffle_delta': delta}))


if __name__ == '__main__':
    main()
