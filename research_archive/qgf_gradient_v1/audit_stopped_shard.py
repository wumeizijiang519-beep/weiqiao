"""Audit retained complete episodes and censored prefix without inventing an outcome."""

import json

import numpy as np

from audit_collection import audit_episode
from data_contract import validate_transition
from wam_runtime import ROOT, file_sha


def main():
    code = ROOT / 'qgf_gradient_v1'
    source = ROOT / 'runs/qgf_gradient_training288_v1_shard0'
    output = code / 'gripper_failure_v1'
    output.mkdir(exist_ok=True)
    manifest = json.loads((code / 'evidence/COHORT_MANIFEST.json').read_text())
    entries = {row['episode_id']: row for row in manifest['partitions']['train']}
    results = []
    for folder in sorted(source.glob('train_*')):
        if (folder / 'EPISODE_COMPLETE').exists():
            result = audit_episode(folder, entries[folder.name])
            results.append(result)
            (output / (folder.name + '_audit.json')).write_text(json.dumps(result, indent=2, sort_keys=True))
            print('COMPLETE_EPISODE_AUDIT_PASS', folder.name, flush=True)
    partial = source / 'train_0030'
    previous_next = None
    prefix = []
    for path in sorted(partial.glob('transition_*/transition.npz')):
        with np.load(path, allow_pickle=False) as loaded:
            data = {key: loaded[key].copy() for key in loaded.files}
        result = validate_transition(data, previous_next)
        previous_next = result.pop('next_obs')
        prefix.append({**result, 'path': str(path), 'actual_length': int(data['actual_length']),
                       'terminal': bool(data['terminal']), 'sha256': file_sha(path)})
    report = {'status': 'STOPPED_DATA_RETAINED_NOT_FULL_COHORT_ADMITTED',
              'complete_episode_audits': results, 'complete_episode_count': len(results),
              'censored_episode': 'train_0030', 'censored_prefix': prefix,
              'censored_prefix_actual_steps': sum(row['actual_length'] for row in prefix),
              'censored_episode_policy_outcome': None,
              'failed_candidate_boundary_actions_executed': 0,
              'original_failed_bank_available': (partial / 'transition_0021/proposals.npz').exists(),
              'scope': 'Preservation audit only. No completed episode rerun, no invented failure label, no critic fitting.'}
    (output / 'PRESERVATION_AUDIT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({key: value for key, value in report.items()
                      if key not in ['complete_episode_audits', 'censored_prefix']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
