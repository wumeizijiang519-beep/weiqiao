"""Independent audit for the proposed failure-critical training cohort."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


TAG = 'failure-critical-boundary-v1:'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def independent_boundary(lengths, event):
    choices = [(index, sum(lengths[index:event + 1])) for index in range(event + 1)]
    choices = [row for row in choices if 16 <= row[1] <= 32]
    return sorted(choices)[0] if choices else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-result', type=Path, required=True)
    parser.add_argument('--cohort', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    dataset = json.loads(args.dataset_result.read_text())
    cohort = json.loads(args.cohort.read_text())
    errors = []
    if dataset.get('status') != 'ADMIT_FOR_RL_QUALIFICATION' or dataset.get('episodes') != 288:
        errors.append('dataset_gate')
    entries = cohort.get('entries', [])
    if len(entries) != 16 or len({row['physical_input_group'] for row in entries}) != 16:
        errors.append('population')

    eligible_by_group = {}
    raw_by_id = {row['episode_id']: row for row in dataset['entries']}
    for source in sorted(dataset['entries'], key=lambda row: row['episode_id']):
        if not source.get('audit_pass') or not source.get('success'):
            continue
        summary_path = Path(source['episode_directory']) / 'summary.json'
        if sha(summary_path) != source['summary_sha256']:
            errors.append(source['episode_id'] + ':summary_sha')
            continue
        summary = json.loads(summary_path.read_text())
        events = [i for i, row in enumerate(summary['transitions']) if float(row['reward_sum']) > 0.]
        if not events:
            errors.append(source['episode_id'] + ':success_without_reward')
            continue
        lengths = [int(row['length']) for row in summary['transitions']]
        boundary = independent_boundary(lengths, events[0])
        if boundary is None:
            continue
        rank = hashlib.sha256((TAG + source['physical_input_group']).encode()).hexdigest()
        eligible_by_group.setdefault(source['physical_input_group'], dict(
            episode_id=source['episode_id'], family=source['family'], rank=rank,
            boundary=boundary, summary=summary, source=source))

    expected = []
    families = sorted({row['family'] for row in eligible_by_group.values()})
    for family in families:
        rows = sorted((row for row in eligible_by_group.values() if row['family'] == family),
                      key=lambda row: row['rank'])
        expected.extend(row['episode_id'] for row in rows[:4])
    if sorted(expected) != sorted(row['episode_id'] for row in entries):
        errors.append('deterministic_selection')

    for row in entries:
        source = raw_by_id.get(row['episode_id'])
        selected = eligible_by_group.get(row['physical_input_group'])
        if source is None or selected is None or selected['episode_id'] != row['episode_id']:
            errors.append(row['episode_id'] + ':source_membership')
            continue
        boundary, distance = selected['boundary']
        if row['boundary_replan'] != boundary or row['logged_steps_to_first_success'] != distance:
            errors.append(row['episode_id'] + ':boundary')
        folder = Path(row['episode_directory'])
        actions, rewards, done, success = [], [], [], []
        for index in range(boundary):
            path = folder / f'transition_{index:04d}/transition.npz'
            receipt = row['transition_receipts'][index]
            if receipt['index'] != index or sha(path) != receipt['sha256']:
                errors.append(row['episode_id'] + f':transition_{index}_sha')
                break
            with np.load(path, allow_pickle=False) as data:
                count = int(data['actual_length'])
                actions.append(data['executed_actions'][:count].astype(np.float32))
                rewards.append(data['rewards'][:count].astype(np.float64))
                done.append(data['step_environment_done'][:count].astype(bool))
                success.append(data['step_success'][:count].astype(bool))
        arrays = (
            np.concatenate(actions) if actions else np.empty((0, 7), np.float32),
            np.concatenate(rewards) if rewards else np.empty(0, np.float64),
            np.concatenate(done) if done else np.empty(0, bool),
            np.concatenate(success) if success else np.empty(0, bool))
        hashes = tuple(hashlib.sha256(value.tobytes()).hexdigest() for value in arrays)
        expected_hashes = tuple(row[name] for name in ('prefix_actions_sha256', 'prefix_rewards_sha256',
                                                        'prefix_done_sha256', 'prefix_success_sha256'))
        if hashes != expected_hashes or len(arrays[0]) != row['prefix_steps']:
            errors.append(row['episode_id'] + ':prefix_receipt')
        observation = Path(row['boundary_observation_path'])
        if sha(observation) != row['boundary_observation_sha256']:
            errors.append(row['episode_id'] + ':boundary_observation')
    family_counts = {family: sum(row['family'] == family for row in entries) for family in families}
    if len(family_counts) != 4 or set(family_counts.values()) != {4}:
        errors.append('family_balance')
    result = dict(status='FAILURE_CRITICAL_BOUNDARY_V1_COHORT_AUDIT_PASS' if not errors
                  else 'FAILURE_CRITICAL_BOUNDARY_V1_COHORT_AUDIT_FAIL', errors=errors,
        groups=len(entries), family_counts=family_counts, eligible_physical_groups=len(eligible_by_group),
        cohort_sha256=sha(args.cohort), dataset_result_sha256=sha(args.dataset_result),
        gpu_execution_authorized=False)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / result['status']).touch()
    (args.output.parent / 'REPORT_SHA256').write_text(sha(args.output) + '  ' + args.output.name + '\n')
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()

