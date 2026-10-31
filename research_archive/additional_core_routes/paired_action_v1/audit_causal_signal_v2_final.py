"""Independent structural and statistical audit of frozen Causal Signal V2."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def horizon(rows, success_key, fraction_key):
    discordant = [row for row in rows if len(set(row[success_key])) > 1]
    binary_families = sorted({row['family'] for row in discordant})
    families = defaultdict(list)
    for row in rows:
        values = np.asarray(row[fraction_key], dtype=np.float64)
        if values.shape != (8,) or not np.isfinite(values).all():
            raise RuntimeError('Invalid eight-candidate dense endpoint')
        families[row['family']].append(float(values.max() - values.min()))
    rng = np.random.default_rng(202641101)
    dense_reports, dense_passing = {}, []
    for family in sorted(families):
        values = np.asarray(families[family], dtype=np.float64)
        samples = values[rng.integers(0, len(values), size=(10000, len(values)))]
        lower, upper = np.quantile(samples.mean(1), [.025, .975])
        passed = bool(lower > 0.)
        dense_reports[family] = dict(groups=len(values), mean_effect=float(values.mean()),
            ci95=[float(lower), float(upper)], passes=passed)
        if passed:
            dense_passing.append(family)
    binary_pass = len(rows) >= 12 and len(discordant) >= 4 and len(binary_families) >= 2
    dense_pass = len(rows) >= 12 and len(dense_passing) >= 2
    return dict(complete_groups=len(rows), binary_discordant_groups=len(discordant),
        binary_discordant_families=binary_families, dense_family_reports=dense_reports,
        dense_passing_families=dense_passing, binary_signal_pass=binary_pass,
        dense_critic_signal_pass=dense_pass,
        status='BINARY_SIGNAL_PASS' if binary_pass else
               'DENSE_CRITIC_SIGNAL_PASS' if dense_pass else 'NO_SIGNAL')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--final-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    final = json.loads(args.final_report.read_text())
    rows = final['results']
    errors = []
    if len(rows) != 16 or len({row['episode_id'] for row in rows}) != 16:
        errors.append('population_not_16_unique')
    for row in rows:
        episode = row['episode_id']
        parent = (args.root / 'paired_action_v1/causal_signal_v2_pilot' if episode == 'train_0205'
                  else args.root / 'paired_action_v1/causal_signal_v2_remaining')
        folder = parent / episode
        if not (folder / 'GROUP_COMPLETE').exists():
            errors.append(episode + ':missing_group_complete')
            continue
        if row.get('status') != 'PAIRED_GROUP_COMPLETE' or len(row.get('branches', [])) != 8:
            errors.append(episode + ':invalid_group_inventory')
            continue
        if sorted(branch['candidate_index'] for branch in row['branches']) != list(range(8)):
            errors.append(episode + ':candidate_inventory')
        for branch in row['branches']:
            index = branch['candidate_index']
            candidate = folder / f'candidate_{index}'
            trajectory = candidate / 'trajectory.npz'
            video = candidate / 'rollout.mp4'
            saved = json.loads((candidate / 'result.json').read_text())
            if saved != branch:
                errors.append(f'{episode}:{index}:branch_result_mismatch')
            if sha(trajectory) != branch['trajectory_sha256'] or sha(video) != branch['video_sha256']:
                errors.append(f'{episode}:{index}:artifact_hash')
            with np.load(trajectory, allow_pickle=False) as data:
                steps = branch['steps']
                if (data['actions'].shape != (steps, 7) or data['rewards'].shape != (steps,)
                        or data['done'].shape != (steps,) or data['success'].shape != (steps,)
                        or data['sim_states'].shape[0] != steps
                        or not all(np.isfinite(data[key]).all() for key in ('actions', 'rewards', 'sim_states'))):
                    errors.append(f'{episode}:{index}:trajectory_contract')
                if abs(float(data['rewards'].sum()) - branch['return']) > 1e-9:
                    errors.append(f'{episode}:{index}:return')
                if steps < 32 and not (branch['environment_done'] or branch['success']):
                    errors.append(f'{episode}:{index}:invalid_early_stop')
            if branch['commit_max_error'] > 1e-6:
                errors.append(f'{episode}:{index}:commit_error')
    clean = [row for row in rows if row.get('status') == 'PAIRED_GROUP_COMPLETE']
    independent16 = horizon(clean, 'successes_at_16', 'goal_fractions_at_16')
    independent32 = horizon(clean, 'successes', 'final_goal_fractions')
    if independent16 != final['horizon16']:
        errors.append('horizon16_recompute_mismatch')
    if independent32 != final['horizon32']:
        errors.append('horizon32_recompute_mismatch')
    expected = ('CAUSAL_SIGNAL_ADMIT' if independent16['status'] != 'NO_SIGNAL'
                or independent32['status'] != 'NO_SIGNAL'
                else 'NO_EXTENDED_NATIVE_ACTION_VALUE_SIGNAL')
    if final['status'] != expected:
        errors.append('final_status_mismatch')
    result = dict(status='CAUSAL_SIGNAL_V2_FINAL_INDEPENDENT_AUDIT_PASS' if not errors
                  else 'CAUSAL_SIGNAL_V2_FINAL_INDEPENDENT_AUDIT_FAIL', errors=errors,
        groups=len(clean), branches=sum(len(row.get('branches', [])) for row in clean),
        final_status=final['status'], final_report_sha256=sha(args.final_report),
        horizon16=independent16, horizon32=independent32)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / result['status']).touch()
    (args.output.parent / 'REPORT_SHA256').write_text(sha(args.output) + '  ' + args.output.name + '\n')
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

