"""Inspect pinned initial-state tensors without model/simulator or outcome use."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
import torch

from cohort_audit import ROOT, OUT, sha


def main():
    catalogue = json.loads(OUT.read_text())
    states, groups, tasks = {}, {}, []
    for record in catalogue['records']:
        path = Path(record['initial_state_path'])
        if not path.exists() or not record['bddl_exists']:
            raise RuntimeError('Missing official asset: ' + record['name'])
        if str(path) not in states:
            array = np.asarray(torch.load(path, map_location='cpu', weights_only=False))
            if '_add_' in path.name or '_level' in path.name:
                array = array.reshape(1, -1)
            if array.ndim != 2 or not np.isfinite(array).all():
                raise ValueError('Invalid official state array: ' + str(path))
            states[str(path)] = {
                'file_sha256': sha(path), 'shape': list(array.shape),
                'state_hashes': [hashlib.sha256(np.asarray(row, dtype='<f8').tobytes()).hexdigest()
                                 for row in array],
            }
        entries = []
        for index, state_sha in enumerate(states[str(path)]['state_hashes']):
            group = hashlib.sha256((record['family'] + '|' + state_sha).encode()).hexdigest()
            groups.setdefault(group, {'family': record['family'], 'state_sha256': state_sha,
                                      'categories': set(), 'records': []})
            groups[group]['categories'].add(record['category'])
            groups[group]['records'].append([record['task_id'], index])
            entries.append(group)
        tasks.append({**record, 'physical_input_groups_by_init_index': entries})
    result = {
        'status': 'INPUT_STATE_ALIAS_AUDIT_NOT_SIMULATOR_RESTORE_OR_LAUNCH_ADMISSION',
        'catalogue_sha256': sha(OUT), 'states': states,
        'groups': {key: {**value, 'categories': sorted(value['categories'])} for key, value in groups.items()},
        'tasks': tasks, 'family_group_counts': dict(Counter(value['family'] for value in groups.values())),
        'limits': ['Raw initialized state equality is a conservative grouping rule.',
                   'Actual environment state after reset/dummy wait still requires collector verification.',
                   'Underlying checkpoint pretraining exposure is not known; disjointness concerns this adaptation experiment.'],
    }
    destination = ROOT / 'qgf_gradient_v1/evidence/state_group_audit.json'
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({'status': result['status'], 'family_group_counts': result['family_group_counts'],
                      'state_files': len(states), 'total_groups': len(groups)}, indent=2))


if __name__ == '__main__':
    main()
