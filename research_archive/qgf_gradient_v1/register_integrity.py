"""Freeze four integrity entries using only the already frozen manifest order."""

import json

from wam_runtime import MANIFEST_SHA, ROOT, file_sha


def main():
    directory = ROOT / 'qgf_gradient_v1'
    manifest_path = directory / 'evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Frozen manifest changed')
    manifest = json.loads(manifest_path.read_text())
    chosen = [next(entry for entry in manifest['partitions']['train'] if entry['family'] == family)
              for family in manifest['families']]
    result = {
        'version': 'collector_integrity_v1_20261026',
        'episode_ids': [entry['episode_id'] for entry in chosen],
        'selection_rule': 'First training entry of each family in frozen manifest order, before any new outcome.',
        'manifest_sha256': MANIFEST_SHA, 'partition': 'train',
        'count_once_in_full_training_cohort': True, 'class_balance_gate': False,
        'max_wall_seconds': 3600, 'gpu_count': 1, 'maximum_initial_integrity_attempts': 2,
        'aggregate_integrity_gpu_hour_cap': 2, 'counts_against_collection_gpu_hour_cap': 24,
        'stopping': 'Unknown errors stop. Completed episodes must not be replayed. No outcome-based replacements.',
        'settings': {'candidate_seeds': [10000, 11000, 12000, 13000],
                     'horizon': 32, 'replan': 10, 'model_step_limit': 700, 'dummy_wait': 30,
                     'actual_rewards_only': True, 'unexecuted_labels': 'NaN',
                     'tolerance': 1e-6, 'compile': True, 'mixed_precision': 'bf16'},
        'preliminary_cost_basis': 'Stage0 loaded model and compiled native inference in431s; warm chunk0.12-2.01s. Four full trajectories are capped at1GPUh; full288 forecast awaits measured integrity p90.',
        'source_sha256': {name: file_sha(directory / name) for name in
                          ['collect.py', 'data_contract.py', 'wam_runtime.py', 'audit_collection.py',
                           'core.py', 'run_collector.sh', 'COLLECTOR_CONTRACT_V1.md']},
    }
    destination = directory / 'COLLECTOR_INTEGRITY_V1.json'
    if destination.exists():
        raise RuntimeError('Never overwrite frozen registration')
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
