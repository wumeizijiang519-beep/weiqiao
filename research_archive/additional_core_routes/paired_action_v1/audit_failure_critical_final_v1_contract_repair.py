"""Independent structural and statistical audit of Failure-Critical Boundary V1."""

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
    rng = np.random.default_rng(202641401)
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
    parser.add_argument('--pilot', type=Path, required=True)
    parser.add_argument('--remaining', type=Path, required=True)
    parser.add_argument('--final-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    final = json.loads(args.final_report.read_text())
    rows = final['results']
    pilot = json.loads((args.pilot / 'REPORT.json').read_text())
    remaining = json.loads((args.remaining / 'REPORT.json').read_text())
    pilot_ids = {row['episode_id'] for row in pilot['results']}
    errors = []
    if len(rows) != 16 or len({row['episode_id'] for row in rows}) != 16:
        errors.append('population_not_16_unique')
    for row in rows:
        episode = row['episode_id']
        parent = args.pilot if episode in pilot_ids else args.remaining
        folder = parent / episode
        if row.get('status') == 'GROUP_UNAVAILABLE':
            if not (folder / 'FAILED.txt').exists():
                errors.append(episode + ':missing_failure_receipt')
            continue
        if not (folder / 'GROUP_COMPLETE').exists():
            errors.append(episode + ':missing_group_complete')
            continue
        if row.get('status') != 'PAIRED_GROUP_COMPLETE' or len(row.get('branches', [])) != 8:
            errors.append(episode + ':invalid_group_inventory')
            continue
        if sorted(branch['candidate_index'] for branch in row['branches']) != list(range(8)):
            errors.append(episode + ':candidate_inventory')
        bank_path = folder / 'bank.npz'
        with np.load(bank_path, allow_pickle=False) as bank_data:
            bank = np.asarray(bank_data['candidates_native'], dtype=np.float32)
            replay_error = float(bank_data['candidate0_replay_error'])
        if (bank.shape != (8, 32, 7) or not np.isfinite(bank).all()
                or len({hashlib.sha256(value.tobytes()).hexdigest() for value in bank}) != 8):
            errors.append(episode + ':bank_contract')
        if replay_error > 1e-6:
            errors.append(episode + ':candidate0_replay')
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
                if data['actions'].shape == (steps, 7):
                    commit = float(np.max(np.abs(data['actions'] - bank[index, :steps])))
                    if commit > 1e-6:
                        errors.append(f'{episode}:{index}:independent_commit')
                if bool(data['success'][-1]) != branch['success']:
                    errors.append(f'{episode}:{index}:success_receipt')
                if bool(data['done'][-1]) != branch['environment_done']:
                    errors.append(f'{episode}:{index}:done_receipt')
                if steps < 32 and not (branch['environment_done'] or branch['success']):
                    errors.append(f'{episode}:{index}:invalid_early_stop')
            if branch['commit_max_error'] > 1e-6:
                errors.append(f'{episode}:{index}:commit_error')
            # The frozen contract requires the policy-returned dual-camera input
            # to match. Direct renderer hashes are retained as metadata only.
            direct_hashes_present = all(
                isinstance(branch[key], str) and len(branch[key]) == 64
                for key in ('boundary_direct_raster_hash', 'bank_boundary_direct_raster_hash'))
            if not (branch['policy_observation_equal_audit_only']
                    and branch['branch_policy_observation_hash'] == branch['bank_policy_observation_hash']
                    and direct_hashes_present):
                errors.append(f'{episode}:{index}:boundary_receipt')
    clean = [row for row in rows if row.get('status') == 'PAIRED_GROUP_COMPLETE']
    independent16 = horizon(clean, 'successes_at_16', 'goal_fractions_at_16')
    independent32 = horizon(clean, 'successes', 'final_goal_fractions')
    if independent16 != final['horizon16']:
        errors.append('horizon16_recompute_mismatch')
    if independent32 != final['horizon32']:
        errors.append('horizon32_recompute_mismatch')
    expected = ('FAILURE_CRITICAL_ACTION_VALUE_SIGNAL_ADMIT' if independent16['status'] != 'NO_SIGNAL'
                or independent32['status'] != 'NO_SIGNAL'
                else 'NO_FAILURE_CRITICAL_ACTION_VALUE_SIGNAL')
    if final['status'] != expected:
        errors.append('final_status_mismatch')
    if final.get('complete_groups') != len(clean) or final.get('unavailable_groups') != 16 - len(clean):
        errors.append('completion_accounting')
    result = dict(status='FAILURE_CRITICAL_BOUNDARY_V1_FINAL_AUDIT_PASS' if not errors
                  else 'FAILURE_CRITICAL_BOUNDARY_V1_FINAL_AUDIT_FAIL', errors=errors,
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

