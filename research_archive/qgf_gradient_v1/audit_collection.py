"""Independent file-based checks before prospective data enter critic training."""

import argparse
from collections import Counter
import json
from pathlib import Path

import imageio.v2 as imageio
import numpy as np

from data_contract import (OBS_KEYS, array_hash, load_rng, observation_hash,
                           rng_hash, validate_transition)
from wam_runtime import MANIFEST_SHA, ROOT, file_sha


def audit_episode(folder, entry):
    summary = json.loads((folder / 'summary.json').read_text())
    config = json.loads((folder / 'config.json').read_text())
    if config != entry or summary['episode_id'] != entry['episode_id']:
        raise ValueError('Manifest/episode mismatch')
    selection_rng = np.random.default_rng(entry['selection_seed'])
    previous_next = None
    remaining = 700
    counts = Counter()
    maximum_commit_error = 0.
    returns = 0.
    diversity = []
    paths = sorted(folder.glob('transition_*/transition.npz'))
    if len(paths) != summary['replans'] or len(list(folder.glob('observation_*.npz'))) != len(paths) + 1:
        raise ValueError('Incomplete transition or R+1 observation sequence')
    for index, path in enumerate(paths):
        if path.parent.name != f'transition_{index:04d}':
            raise ValueError('Noncontiguous transition sequence')
        with np.load(path, allow_pickle=False) as loaded:
            data = {key: loaded[key].copy() for key in loaded.files}
        expected = int(selection_rng.integers(0, 4))
        if int(data['selected_index']) != expected:
            raise ValueError('Selection sequence differs from frozen seed')
        if int(data['remaining_before']) != remaining:
            raise ValueError('Episode finite-horizon discontinuity')
        checked = validate_transition(data, previous_next)
        previous_next = checked['next_obs']
        remaining = int(data['remaining_after'])
        counts[expected] += 1
        returns += checked['reward_sum']
        maximum_commit_error = max(maximum_commit_error, checked['commit_error'])
        if any(str(stored) != array_hash(action) for stored, action in
               zip(data['candidate_hashes'], data['candidates_native'])):
            raise ValueError('Candidate hash mismatch')
        post0 = load_rng(path.parent / 'rng_candidate_0_post.npz')
        committed = load_rng(path.parent / 'rng_caller_committed.npz')
        if rng_hash(post0) != rng_hash(committed) or rng_hash(committed) != str(data['caller_rng_hash']):
            raise ValueError('Saved caller RNG differs from candidate0 post-state')
        for rng_path in path.parent.glob('rng_*.npz'):
            load_rng(rng_path)
        for prefix, obs_index in [('current', index), ('next', index + 1)]:
            with np.load(folder / f'observation_{obs_index:04d}.npz', allow_pickle=False) as loaded:
                saved = {key: loaded[key] for key in OBS_KEYS}
                recorded = {key: data[prefix + '_' + key] for key in OBS_KEYS}
                if observation_hash(saved) != observation_hash(recorded):
                    raise ValueError('R+1 observation does not match transition')
        feedback = np.load(path.parent / 'execution_progress.npz', allow_pickle=False)
        for key in ['executed_actions', 'rewards', 'sim_states']:
            if not np.array_equal(feedback[key], data[key]):
                raise ValueError('Progress feedback differs from transition')
        feedback.close()
        if not bool(data['terminal']) and index == len(paths) - 1:
            raise ValueError('Incomplete terminal trajectory')
        if bool(data['terminal']) and index != len(paths) - 1:
            raise ValueError('Action executed after terminal state')
        if bool(data['environment_done']) != bool(data['step_environment_done'][-1]):
            raise ValueError('Actual done feedback mismatch')
        if bool(data['success']) != bool(data['step_success'][-1]):
            raise ValueError('Actual success feedback mismatch')
        if file_sha(path) != summary['transitions'][index]['transition_sha256']:
            raise ValueError('Transition changed after collection')
        bank = data['candidates_native']
        diversity.extend(float(np.abs(bank[i] - bank[j]).mean()) for i in range(4) for j in range(i))
    if summary['model_steps'] != 700 - remaining:
        raise ValueError('Incorrect episode step total')
    if [counts[i] for i in range(4)] != summary['selected_counts']:
        raise ValueError('Incorrect selection counts')
    if paths:
        if summary['success'] != bool(data['success']) or summary['time_limit'] != bool(data['time_limit']):
            raise ValueError('Summary outcome differs from final transition')
    elif not summary['preboundary_terminal']:
        raise ValueError('No transition without a recorded pre-boundary terminal')
    if file_sha(folder / 'rollout.mp4') != summary['video_sha256']:
        raise ValueError('Video changed')
    reader = imageio.get_reader(folder / 'rollout.mp4')
    frames = sum(1 for _ in reader)
    reader.close()
    if frames != 31 + summary['model_steps'] or frames != summary['video_frames']:
        raise ValueError('Incomplete video')
    return {'episode_id': entry['episode_id'], 'audit_pass': True, 'success': summary['success'],
            'replans': len(paths), 'model_steps': summary['model_steps'],
            'selected_counts': [counts[i] for i in range(4)], 'reward_sum': returns,
            'commit_error': maximum_commit_error,
            'pairwise_mad_min': min(diversity) if diversity else None,
            'physical_input_group': entry['physical_input_group'],
            'wall_seconds': summary['wall_seconds'], 'video_frames': frames}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    manifest_path = ROOT / 'qgf_gradient_v1/evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise ValueError('Frozen manifest changed')
    manifest = json.loads(manifest_path.read_text())
    entries = {row['episode_id']: row for row in manifest['partitions']['train']}
    registration = json.loads((args.run / 'registration.json').read_text())
    reports = [audit_episode(args.run / episode_id, entries[episode_id])
               for episode_id in registration['episode_ids']]
    durations = np.asarray([row['wall_seconds'] for row in reports])
    result = {'status': 'COLLECTOR_INTEGRITY_PASS', 'episodes': reports,
              'successes': sum(row['success'] for row in reports),
              'failures': sum(not row['success'] for row in reports),
              'p90_episode_seconds': float(np.quantile(durations, .9)),
              'cohort_class_gate_applied': False,
              'scope': 'Integrity/cost only. These entries count once in the fixed training cohort.',
              'collection_report_sha256': file_sha(args.run / 'report.json')}
    (args.run / 'INDEPENDENT_AUDIT.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.run / 'COLLECTOR_AUDIT_PASS').touch()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
