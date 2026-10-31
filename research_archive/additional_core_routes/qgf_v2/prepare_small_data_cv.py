"""Separate diagnostic CV, without altering the stopped standard60 contract."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import numpy as np
from features import encode_states, training_scaler
from validate_transitions import validate_run

SOURCE_SHA = 'bde57dcd15dddfd07d63fe5209a3faded3e8b7f1e63ddb217a84718e33e74483'
CV_SEED = 202621500


def folds_for(rows):
    if len(rows) != 60 or len({r['seed'] for r in rows}) != 60:
        raise ValueError('need exact60 unique episodes')
    successes = sorted((r for r in rows if r['success']), key=lambda r: r['seed'])
    failures = sorted((r for r in rows if not r['success']), key=lambda r: r['seed'])
    if (len(successes), len(failures)) != (56, 4):
        raise ValueError('frozen56S4F diagnostic contract required')
    rng = random.Random(CV_SEED)
    rng.shuffle(successes)
    rng.shuffle(failures)
    result = []
    for fold in range(4):
        validation = successes[fold * 14:(fold + 1) * 14] + [failures[fold]]
        held = {r['seed'] for r in validation}
        train = [r for r in rows if r['seed'] not in held]
        result.append((sorted(train, key=lambda r: r['seed']), sorted(validation, key=lambda r: r['seed'])))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    stage = args.root / 'qgf_v2'
    output = stage / 'small_data_cv_v1' / 'data'
    if output.exists():
        raise FileExistsError(output)
    audit_path = stage / 'standard60_combined_audit.json'
    if hashlib.sha256(audit_path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('frozen source audit changed')
    frozen = json.loads(audit_path.read_text())
    rows = []
    for seed in (202615100, 202615200, 202615300, 202615400, 202616100, 202616200):
        run = stage / 'runs' / f'standard_train10_seed{seed}'
        if not (run / 'COLLECTION_COMPLETE').exists():
            raise ValueError('source shard incomplete')
        rows.extend(validate_run(run))
    if rows != frozen['episodes']:
        raise ValueError('source records/SHA no longer match retained audit')
    splits = folds_for(rows)
    cache = {}
    for row in rows:
        with np.load(row['file'], allow_pickle=False) as raw:
            cache[row['seed']] = {'states': encode_states(raw), 'actions': raw['action_chunks'],
                                 'rewards': raw['rewards'], 'steps': raw['executed_steps'],
                                 'terminal': raw['finite_horizon_terminal'], 'seed': raw['seed'], 'success': raw['success']}
    output.mkdir(parents=True)
    summary = {'schema': 'qgf_v2_small_data_cv_v1', 'source_audit_sha256': SOURCE_SHA,
               'split_seed': CV_SEED, 'diagnostic_only': True, 'folds': []}
    for fold, (train, validation) in enumerate(splits):
        directory = output / f'fold{fold}'
        directory.mkdir()
        manifest = {'schema': summary['schema'], 'source_audit_sha256': SOURCE_SHA,
                    'split_seed': CV_SEED, 'fold': fold, 'dataset_episode_count': 60,
                    'feature_source': 'fixed96px RGB16patch mean/std, NOT WAM hidden features',
                    'state_dim': 701, 'action_shape': [10, 16],
                    'normalization': 'fold-training-only episode-equal mean/std', 'partitions': {}}
        for name, records in (('train', train), ('validation', validation)):
            manifest['partitions'][name] = []
            for row in records:
                path = directory / f"{name}_{row['seed']}.npz"
                np.savez_compressed(path, **cache[row['seed']])
                manifest['partitions'][name].append({**row, 'feature_file': path.name,
                    'feature_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        scaler = directory / 'training_scaler.npz'
        np.savez(scaler, **training_scaler([cache[r['seed']] for r in train]))
        manifest['scaler_sha256'] = hashlib.sha256(scaler.read_bytes()).hexdigest()
        path = directory / 'manifest.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        (directory / 'COMPLETE').touch()
        summary['folds'].append({'fold': fold, 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'train_seeds': [r['seed'] for r in train], 'validation_seeds': [r['seed'] for r in validation]})
    (output / 'cv_manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'COMPLETE').touch()
    print(json.dumps({'status': 'CV_DATA_COMPLETE', 'folds': 4, 'train_each': '42S3F', 'validation_each': '14S1F'}))


if __name__ == '__main__':
    main()
