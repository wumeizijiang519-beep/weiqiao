"""Build the deterministic training-only failure-critical boundary cohort."""

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


def choose_boundary(lengths, event_index):
    """Return the farthest archived boundary no more than 32 steps pre-event."""
    eligible = []
    for boundary in range(event_index + 1):
        distance = sum(lengths[boundary:event_index + 1])
        if 16 <= distance <= 32:
            eligible.append((boundary, distance))
    return min(eligible) if eligible else None


def inspect_entry(entry):
    if not entry.get('audit_pass') or not entry.get('success'):
        return None
    folder = Path(entry['episode_directory'])
    summary_path = folder / 'summary.json'
    if sha(summary_path) != entry['summary_sha256']:
        raise RuntimeError('Certified summary changed: ' + entry['episode_id'])
    summary = json.loads(summary_path.read_text())
    if not summary.get('success') or summary['episode_id'] != entry['episode_id']:
        raise RuntimeError('Success inventory mismatch')
    lengths = [int(row['length']) for row in summary['transitions']]
    events = [i for i, row in enumerate(summary['transitions']) if float(row['reward_sum']) > 0.]
    if not events:
        raise RuntimeError('Official success lacks positive reward transition')
    event = events[0]
    selected = choose_boundary(lengths, event)
    if selected is None:
        return None
    boundary, distance = selected
    prefix_actions, prefix_rewards, prefix_done, prefix_success = [], [], [], []
    transition_receipts = []
    for index in range(boundary):
        path = folder / f'transition_{index:04d}/transition.npz'
        expected = summary['transitions'][index]['transition_sha256']
        if sha(path) != expected:
            raise RuntimeError('Certified transition changed')
        with np.load(path, allow_pickle=False) as data:
            actual = int(data['actual_length'])
            prefix_actions.append(data['executed_actions'][:actual].astype(np.float32))
            prefix_rewards.append(data['rewards'][:actual].astype(np.float64))
            prefix_done.append(data['step_environment_done'][:actual].astype(bool))
            prefix_success.append(data['step_success'][:actual].astype(bool))
        transition_receipts.append(dict(index=index, sha256=expected, actual_length=actual))
    actions = np.concatenate(prefix_actions) if prefix_actions else np.empty((0, 7), dtype=np.float32)
    rewards = np.concatenate(prefix_rewards) if prefix_rewards else np.empty(0, dtype=np.float64)
    done = np.concatenate(prefix_done) if prefix_done else np.empty(0, dtype=bool)
    success = np.concatenate(prefix_success) if prefix_success else np.empty(0, dtype=bool)
    observation = folder / f'observation_{boundary:04d}.npz'
    if not observation.exists() or actions.ndim != 2 or actions.shape[1:] != (7,):
        raise RuntimeError('Boundary archive incomplete')
    return dict(episode_id=entry['episode_id'], family=entry['family'],
        physical_input_group=entry['physical_input_group'], category=entry['category'],
        group_oof_fold=entry['group_oof_fold'], episode_directory=str(folder),
        summary_sha256=entry['summary_sha256'], environment_seed=summary['environment_seed'],
        initial_state_index=summary['initial_state_index'], initial_state_path=summary['initial_state_path'],
        initial_file_sha256=summary['initial_file_sha256'], bddl_path=summary['bddl_path'],
        bddl_sha256=summary['bddl_sha256'], task_description=summary['task_description'],
        task_id=summary['task_id'], dummy_steps=summary['dummy_steps'],
        boundary_replan=boundary, boundary_model_step=int(sum(lengths[:boundary])),
        logged_steps_to_first_success=distance, first_reward_replan=event,
        boundary_observation_path=str(observation), boundary_observation_sha256=sha(observation),
        prefix_actions_sha256=hashlib.sha256(actions.tobytes()).hexdigest(),
        prefix_rewards_sha256=hashlib.sha256(rewards.tobytes()).hexdigest(),
        prefix_done_sha256=hashlib.sha256(done.tobytes()).hexdigest(),
        prefix_success_sha256=hashlib.sha256(success.tobytes()).hexdigest(),
        prefix_steps=len(actions), transition_receipts=transition_receipts,
        selection_rank_sha256=hashlib.sha256((TAG + entry['physical_input_group']).encode()).hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset-result', type=Path, required=True)
    parser.add_argument('--dataset-result-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if sha(args.dataset_result) != args.dataset_result_sha256:
        raise RuntimeError('Frozen dataset result changed')
    dataset = json.loads(args.dataset_result.read_text())
    if dataset['status'] != 'ADMIT_FOR_RL_QUALIFICATION' or dataset['episodes'] != 288:
        raise RuntimeError('Frozen training cohort gate missing')
    by_group = {}
    inspected, eligible = 0, 0
    for entry in sorted(dataset['entries'], key=lambda row: row['episode_id']):
        record = inspect_entry(entry)
        inspected += 1
        if record is None:
            continue
        eligible += 1
        by_group.setdefault(record['physical_input_group'], record)
    by_family = {}
    for record in by_group.values():
        by_family.setdefault(record['family'], []).append(record)
    if len(by_family) != 4:
        raise RuntimeError('Expected exactly four frozen task families')
    selected = []
    family_inventory = {}
    for family in sorted(by_family):
        records = sorted(by_family[family], key=lambda row: row['selection_rank_sha256'])
        family_inventory[family] = dict(eligible_groups=len(records), selected_groups=min(4, len(records)))
        if len(records) < 4:
            raise RuntimeError('Fewer than four eligible groups in family: ' + family)
        selected.extend(records[:4])
    if len(selected) != 16 or len({row['physical_input_group'] for row in selected}) != 16:
        raise RuntimeError('Selected population is not 16 unique physical groups')
    result = dict(status='FAILURE_CRITICAL_BOUNDARY_V1_COHORT_PROPOSED_NOT_AUTHORIZED',
        dataset_result_sha256=args.dataset_result_sha256, inspected_training_episodes=inspected,
        eligible_success_episodes=eligible, eligible_physical_groups=len(by_group),
        family_inventory=family_inventory, entries=selected, groups=16,
        selection_uses_new_candidate_outcomes=False, validation_or_formal_read=False,
        replacement_after_execution_allowed=False)
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / 'COHORT_SHA256').write_text(sha(args.output) + '  ' + args.output.name + '\n')
    print(json.dumps(dict(status=result['status'], family_inventory=family_inventory,
                          eligible_groups=len(by_group), groups=16), indent=2))


if __name__ == '__main__':
    main()

