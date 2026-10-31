"""Read a certified episode into RL arrays; never extract features or fit models."""

import hashlib
import json
from pathlib import Path

import numpy as np

from rl_corpus import episode_arrays


MANIFEST_SHA = '7194f02c8dba2c9ae01fddab1d0c48c169e28f6778e3926a0386dfeff0307af9'
TRANSITION_KEYS = ('selected_index', 'actual_length', 'remaining_before', 'remaining_after',
                   'rewards', 'terminal', 'environment_done', 'success', 'time_limit',
                   'candidate_returns', 'executed_actions', 'candidates_native',
                   'candidates_executed_normalized')


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def checked_json(path, expected_sha):
    if len(expected_sha) != 64 or sha(path) != expected_sha:
        raise ValueError('Frozen certificate/file hash mismatch')
    return json.loads(Path(path).read_text())


def certified_population(path, expected_sha):
    data = checked_json(path, expected_sha)
    if (data['status'] != 'ADMIT_FOR_RL_QUALIFICATION' or data['episodes'] != 288
            or data['manifest_sha256'] != MANIFEST_SHA
            or not data['checks'] or not all(v is True for v in data['checks'].values())):
        raise ValueError('Complete fixed dataset has not been admitted')
    rows = data['entries']
    ids, groups = set(), {}
    for row in rows:
        name, group, fold = row['episode_id'], row['physical_input_group'], row['group_oof_fold']
        if name in ids or fold not in (0, 1, 2) or not row['audit_pass']:
            raise ValueError('Duplicate/unqualified episode or invalid fold')
        if group in groups and groups[group] != fold:
            raise ValueError('Physical-group fold leakage')
        ids.add(name)
        groups[group] = fold
    if len(rows) != 288 or ids != {f'train_{i:04d}' for i in range(288)}:
        raise ValueError('Fixed288-entry union changed')
    return {row['episode_id']: row for row in rows}


def contained_file(root, relative):
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if root not in path.parents:
        raise ValueError('Feature artifact escaped registered directory')
    return path


def read_episode(entry, features, observation_hashes):
    """Low-level codec; production callers must use load_admitted_episode."""
    folder = Path(entry['episode_directory'])
    if not (folder / 'EPISODE_COMPLETE').exists():
        raise ValueError('Episode is incomplete')
    summary = checked_json(folder / 'summary.json', entry['summary_sha256'])
    if (summary['episode_id'] != entry['episode_id']
            or summary['physical_input_group'] != entry['physical_input_group']
            or summary['replans'] != entry['replans']
            or summary['success'] != entry['success']):
        raise ValueError('Episode summary disagrees with certificate')
    count = int(summary['replans'])
    values = np.asarray(features)
    if (values.dtype != np.float32 or values.ndim != 2 or values.shape[0] != count + 1
            or values.shape[1] < 1 or not np.isfinite(values).all()
            or len(observation_hashes) != count + 1):
        raise ValueError('Features must cover finite float32 R+1 actual observations')
    if len(summary['transitions']) != count:
        raise ValueError('Missing logged transitions')
    for number, expected in enumerate(observation_hashes):
        if sha(folder / f'observation_{number:04d}.npz') != expected:
            raise ValueError('Feature observation provenance changed')
    paths = sorted(folder.glob('transition_*/transition.npz'))
    if len(paths) != count:
        raise ValueError('Missing/extra transition files')
    transitions = []
    for number, (path, record) in enumerate(zip(paths, summary['transitions'])):
        if path.parent.name != f'transition_{number:04d}' or sha(path) != record['transition_sha256']:
            raise ValueError('Actual feedback archive changed')
        with np.load(path, allow_pickle=False) as data:
            transitions.append({key: data[key].copy() for key in TRANSITION_KEYS})
    metadata = dict(episode_id=entry['episode_id'], physical_group=entry['physical_input_group'],
                    fold=entry['group_oof_fold'], transitions=count, success=entry['success'])
    if not count:
        # Retain zero-action episodes in the scientific denominator/ledger.
        # There is no observed macro-action target to invent or fit.
        return None, {**metadata, 'fitting_rows': 0, 'zero_transition_episode': True}
    arrays, info = episode_arrays(transitions, values, episode_id=metadata['episode_id'],
                                 physical_group=metadata['physical_group'], fold=metadata['fold'])
    return arrays, {**info, **metadata, 'fitting_rows': count, 'zero_transition_episode': False}


def load_admitted_episode(dataset_path, dataset_sha, feature_root, index_sha, episode_id):
    population = certified_population(dataset_path, dataset_sha)
    root = Path(feature_root)
    index = checked_json(root / 'INDEX.json', index_sha)
    if (index['status'] != 'CURRENT_ONLY_CORPUS_FEATURES_COMPLETE'
            or index['dataset_result_sha256'] != dataset_sha):
        raise ValueError('Features do not belong to admitted dataset')
    encoder = checked_json(contained_file(root, index['encoder_report']), index['encoder_report_sha256'])
    if (encoder['status'] != 'CURRENT_FEATURE_ENCODER_AUDIT_PASS'
            or encoder['dataset_result_sha256'] != dataset_sha
            or encoder['feature_spec']['future_frames'] != 0
            or encoder['features_source_sha256'] != sha(Path(__file__).with_name('features.py'))):
        raise ValueError('Current-only encoder/source qualification missing')
    feature_rows = index['episodes']
    if len(feature_rows) != 288 or {r['episode_id'] for r in feature_rows} != set(population):
        raise ValueError('Feature index dropped/duplicated fixed episodes')
    row = next(r for r in feature_rows if r['episode_id'] == episode_id)
    path = contained_file(root, row['file'])
    if sha(path) != row['sha256']:
        raise ValueError('Frozen feature artifact changed')
    with np.load(path, allow_pickle=False) as data:
        if data.files != ['current_features']:
            raise ValueError('Unexpected/outcome-bearing feature artifact fields')
        values = data['current_features'].copy()
    if values.ndim != 2 or values.shape[1] != encoder['feature_spec']['feature_dimension']:
        raise ValueError('Feature dimension differs from audited encoder')
    return read_episode(population[episode_id], values, row['observation_file_sha256'])
