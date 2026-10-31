"""Build the preregistered four-fold QGF-v3 UNITAS latent diagnostic."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from features import training_scaler

SOURCE_SHA = 'bde57dcd15dddfd07d63fe5209a3faded3e8b7f1e63ddb217a84718e33e74483'
LATENT_MANIFEST_SHA = 'ada05df1d77337ad774bdfc3a27d9b76e3ffd15d19e02cbde11d79a98a9ec997'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    args = parser.parse_args()
    source_cv = args.stage / 'small_data_cv_v1' / 'data'
    latent_root = args.stage / 'unitas_latents_v1'
    output = args.stage / 'unitas_latent_cv_v1' / 'data'
    if output.exists():
        raise FileExistsError(output)
    if sha(latent_root / 'manifest.json') != LATENT_MANIFEST_SHA:
        raise ValueError('frozen latent manifest changed')
    summary = {'schema': 'qgf_v3_unitas_latent_cv_v1', 'source_audit_sha256': SOURCE_SHA,
               'latent_manifest_sha256': LATENT_MANIFEST_SHA, 'diagnostic_only': True, 'folds': []}
    output.mkdir(parents=True)
    for fold in range(4):
        old = source_cv / f'fold{fold}'
        old_manifest = json.loads((old / 'manifest.json').read_text())
        directory = output / f'fold{fold}'
        directory.mkdir()
        manifest = {'schema': summary['schema'], 'fold': fold, 'dataset_episode_count': 60,
                    'split_seed': old_manifest['split_seed'], 'source_audit_sha256': SOURCE_SHA,
                    'latent_manifest_sha256': LATENT_MANIFEST_SHA,
                    'feature_source': 'frozen UNITAS Florence2 pooled visual-language representation plus proprioception/time',
                    'state_dim': 9269, 'action_shape': [10, 16],
                    'normalization': 'fold-training-only episode-equal mean/std', 'partitions': {}}
        cache = {}
        for records in old_manifest['partitions'].values():
            for record in records:
                seed = int(record['seed'])
                if seed in cache:
                    continue
                source_path = Path(record['file'])
                if sha(source_path) != record['sha256']:
                    raise ValueError(f'source SHA mismatch for {seed}')
                latent_path = latent_root / f'seed_{seed}.npz'
                with np.load(source_path, allow_pickle=False) as src, np.load(latent_path, allow_pickle=False) as lat:
                    chunks = len(src['action_chunks'])
                    latent = np.asarray(lat['latent_states'], dtype=np.float32)
                    if latent.shape != (chunks + 1, 9216):
                        raise ValueError(f'latent shape mismatch for {seed}: {latent.shape}')
                    steps = np.append(src['replan_steps'], int(src['final_steps'])).astype(np.float32)
                    remaining = (1 - steps / int(src['task_limit']))[:, None]
                    aux = np.concatenate([src['joint_positions'], src['tcp_pose'], remaining], axis=1).astype(np.float32)
                    states = np.concatenate([latent, aux], axis=1).astype(np.float32)
                    arrays = {'states': states, 'actions': src['action_chunks'].astype(np.float32),
                              'rewards': src['rewards'].astype(np.float32),
                              'steps': src['executed_steps'].astype(np.int64),
                              'terminal': src['finite_horizon_terminal'].astype(bool),
                              'seed': np.asarray(seed), 'success': np.asarray(bool(record['success']))}
                if not all(np.isfinite(v).all() for k, v in arrays.items() if k not in ('terminal', 'success')):
                    raise ValueError(f'nonfinite data for {seed}')
                cache[seed] = arrays
        for name, records in old_manifest['partitions'].items():
            manifest['partitions'][name] = []
            for record in records:
                seed = int(record['seed'])
                path = directory / f'{name}_{seed}.npz'
                np.savez_compressed(path, **cache[seed])
                manifest['partitions'][name].append({**record, 'feature_file': path.name,
                                                     'feature_sha256': sha(path)})
        train = [cache[int(row['seed'])] for row in old_manifest['partitions']['train']]
        scaler_path = directory / 'training_scaler.npz'
        np.savez(scaler_path, **training_scaler(train))
        manifest['scaler_sha256'] = sha(scaler_path)
        manifest_path = directory / 'manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        (directory / 'COMPLETE').touch()
        summary['folds'].append({'fold': fold, 'manifest_sha256': sha(manifest_path)})
    (output / 'cv_manifest.json').write_text(json.dumps(summary, indent=2) + '\n')
    (output / 'COMPLETE').touch()
    print(json.dumps({'status': 'COMPLETE', 'folds': 4, 'state_dim': 9269}))


if __name__ == '__main__':
    main()
