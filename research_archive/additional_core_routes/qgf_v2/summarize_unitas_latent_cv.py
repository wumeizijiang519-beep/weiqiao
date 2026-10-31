"""Create the preregistered final-step QGF-v3 OOF method conclusion."""
import hashlib
import json
from pathlib import Path
import statistics
from v3_conditions import conditions


def main():
    suite = Path(__file__).resolve().parent / 'unitas_latent_cv_v1'
    rows = []
    for condition in conditions():
        directory = suite / 'training' / condition['name']
        if not (directory / 'COMPLETE').exists():
            raise ValueError('all24 fixed runs must complete')
        final = json.loads((directory / 'metrics.jsonl').read_text().splitlines()[-1])
        if final['step'] != 10000:
            raise ValueError('fixed final step required')
        rows.append({**condition, 'final': final,
                     'checkpoint_sha256': hashlib.sha256((directory / 'latest.pt').read_bytes()).hexdigest()})
    aggregate = {}
    for kind in ('action', 'state_only'):
        aggregate[kind] = []
        for seed in range(3):
            folds = [r for r in rows if r['kind'] == kind and r['seed'] == seed]
            episodes = [e for r in folds for e in r['final']['per_episode']]
            if len(episodes) != 60 or len({e['seed'] for e in episodes}) != 60:
                raise ValueError('OOF coverage failure')
            aggregate[kind].append({'seed': seed,
                'common_success_mse': statistics.mean(e['undiscounted_success_mse'] for e in episodes),
                'failure_common_mse': statistics.mean(e['undiscounted_success_mse'] for e in episodes if not e['success']),
                'matched_mc_mse': statistics.mean(e['matched_mc_mse'] for e in episodes),
                'action_shuffle_abs_delta': statistics.mean(r['final']['action_shuffle_abs_delta'] for r in folds)})
    wins = sum(a['common_success_mse'] < b['common_success_mse']
               for a, b in zip(aggregate['action'], aggregate['state_only']))
    shuffle = statistics.mean(r['action_shuffle_abs_delta'] for r in aggregate['action'])
    status = ('DIRECTIONAL_SIGNAL_ADMIT_MATCHED_ONLINE' if wins == 3 and shuffle > 1e-4
              else 'NO_CONVINCING_ACTION_VALUE_EVIDENCE_IN_THIS_DIAGNOSTIC')
    result = {'diagnostic_only': True, 'status': status, 'independent_episodes': 60,
              'independent_failures': 4, 'action_vs_state_only_wins': wins,
              'mean_action_shuffle_abs_delta': shuffle, 'aggregate': aggregate, 'runs': rows,
              'warning': 'This OOF diagnostic gates, but cannot replace, fresh matched online robot evaluation.'}
    (suite / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    lines = ['# QGF v3 UNITAS-Latent Method Conclusion', '', f'Status: {status}', '',
             'All24 runs use fixed final10000-step checkpoints and the frozen four folds.',
             f'Action-aware critic beats same-target state-only in {wins}/3 bootstrap seeds.',
             f'Mean action-shuffle response: {shuffle:.8g}.', '',
             '| Method | Seed | Common MSE | Failure MSE | Matched MC MSE | Shuffle delta |',
             '| --- | --- | --- | --- | --- | --- |']
    for kind, records in aggregate.items():
        for row in records:
            lines.append(f"| {kind} | {row['seed']} | {row['common_success_mse']:.6g} | {row['failure_common_mse']:.6g} | {row['matched_mc_mse']:.6g} | {row['action_shuffle_abs_delta']:.6g} |")
    lines += ['', 'Only four failures are independent. This is a method qualification diagnostic,',
              'not a robot success-rate result. Positive admission requires a fresh matched online test.']
    (suite / 'METHOD_CONCLUSION.md').write_text('\n'.join(lines) + '\n')
    (suite / 'COMPLETE').touch()
    print(json.dumps({'status': status, 'wins': wins, 'shuffle': shuffle}))


if __name__ == '__main__':
    main()
