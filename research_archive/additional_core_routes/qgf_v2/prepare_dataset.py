"""Audit the fixed40 data, freeze a split and export transparent RGB features."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import numpy as np
from features import encode_states, training_scaler
from validate_transitions import validate_run


def split_rows(rows, seed=202615500, total=40, validation_count=8):
    if (total, validation_count, seed) not in ((40, 8, 202615500), (60, 12, 202616500)):
        raise ValueError('unregistered split contract')
    if len(rows) != total or len({r['seed'] for r in rows}) != total:
        raise ValueError('expected fixed total of unique accepted episodes')
    successes = sorted([r for r in rows if r['success']], key=lambda r: r['seed'])
    failures = sorted([r for r in rows if not r['success']], key=lambda r: r['seed'])
    if min(len(successes), len(failures)) < 6:
        raise ValueError('STOP_INSUFFICIENT_CLASSES: need6success and6failure; no expansion')
    rng = random.Random(seed)
    rng.shuffle(successes)
    rng.shuffle(failures)
    val_failures = min(validation_count - 1, len(failures) - 4,
                       max(2, validation_count - len(successes) + 1, round(len(failures) / 5)))
    val_successes = validation_count - val_failures
    validation = failures[:val_failures] + successes[:val_successes]
    train = failures[val_failures:] + successes[val_successes:]
    if len(train) != total - validation_count or len(validation) != validation_count:
        raise ValueError('stratified split size mismatch')
    return sorted(train, key=lambda r: r['seed']), sorted(validation, key=lambda r: r['seed'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--extension20-approved', action='store_true')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    rows = []
    starts = (202615100, 202615200, 202615300, 202615400)
    if args.extension20_approved:
        approval = json.loads((args.root / 'qgf_v2' / 'extension20_proposal_v1.json').read_text())
        if approval['status'] != 'APPROVED_BOUNDED_EXTENSION20':
            raise ValueError('extension approval missing')
        starts += (202616100, 202616200)
    total, validation_count, split_seed = (60, 12, 202616500) if args.extension20_approved else (40, 8, 202615500)
    for start in starts:
        run = args.root / 'qgf_v2' / 'runs' / f'standard_train10_seed{start}'
        if not (run / 'COLLECTION_COMPLETE').exists():
            raise ValueError(f'shard not complete: {start}')
        shard = validate_run(run)
        if len(shard) != 10 or any(not start <= r['seed'] < start + 100 for r in shard):
            raise ValueError('shard count or candidate range mismatch')
        rows.extend(shard)
    excluded = {202615000, 202614000}
    for path in (args.root / 'runs').glob('*/eval/*/episode*.json'):
        result = json.loads(path.read_text())
        excluded.add(int(result['seed']))
    if excluded.intersection(r['seed'] for r in rows):
        raise ValueError('seed overlap with existing evaluation/engineering episodes')
    train, validation = split_rows(rows, split_seed, total, validation_count)
    args.output.mkdir(parents=True)
    manifest = {'schema': 'unitas_v2_rgbstats_dataset_v1', 'split_seed': split_seed,
                'dataset_episode_count': total,
                'feature_source': 'fixed96px RGB16patch mean/std, NOT WAM hidden features',
                'camera_order': ['head', 'left', 'right'], 'state_dim': 701,
                'action_shape': [10, 16], 'remaining_time_in_state': True,
                'normalization': 'training-only episode-equal mean/std',
                'seed_exclusions_checked': sorted(excluded), 'partitions': {}}
    training = []
    for partition, records in (('train', train), ('validation', validation)):
        manifest['partitions'][partition] = []
        for row in records:
            with np.load(row['file'], allow_pickle=False) as raw:
                data = {'states': encode_states(raw), 'actions': raw['action_chunks'],
                        'rewards': raw['rewards'], 'steps': raw['executed_steps'],
                        'terminal': raw['finite_horizon_terminal'],
                        'seed': raw['seed'], 'success': raw['success']}
            path = args.output / f"{partition}_{row['seed']}.npz"
            np.savez_compressed(path, **data)
            manifest['partitions'][partition].append({**row, 'feature_file': path.name,
                'feature_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
            if partition == 'train':
                training.append(data)
    np.savez(args.output / 'training_scaler.npz', **training_scaler(training))
    manifest['scaler_sha256'] = hashlib.sha256((args.output / 'training_scaler.npz').read_bytes()).hexdigest()
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (args.output / 'COMPLETE').touch()
    print(json.dumps({name: {'episodes': len(part), 'failures': sum(not r['success'] for r in part)}
                      for name, part in manifest['partitions'].items()}))


if __name__ == '__main__':
    main()
