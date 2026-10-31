"""Validate transition archives against actual official episode result seeds."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def validate_run(run):
    rows = []
    provenance = json.loads((run / 'provenance.json').read_text())
    task = provenance['task']
    for path in sorted((run / 'trajectories').glob('trajectory_*.npz')):
        metadata = json.loads(path.with_suffix('.json').read_text())
        with np.load(path, allow_pickle=False) as data:
            seed = int(data['seed'])
            actions = data['action_chunks']
            count = len(actions)
            if count < 1 or actions.shape[1:] != (10, 16):
                raise ValueError('invalid action dimensions')
            for key, tail in (('head_rgb', (96, 96, 3)), ('left_rgb', (96, 96, 3)),
                              ('right_rgb', (96, 96, 3)), ('joint_positions', (38,)),
                              ('tcp_pose', (14,))):
                if data[key].shape != (count + 1, *tail):
                    raise ValueError(f'{key}: expected R+1 observations')
            for key in data.files:
                if np.issubdtype(data[key].dtype, np.number) and not np.isfinite(data[key]).all():
                    raise ValueError(f'{key}: nonfinite array')
            lengths = data['executed_steps']
            if lengths.shape != (count,) or (lengths < 1).any() or (lengths > 10).any():
                raise ValueError('invalid executed lengths')
            np.testing.assert_array_equal(np.diff(np.append(data['replan_steps'], data['final_steps'])), lengths)
            if int(lengths.sum()) != int(data['final_steps']):
                raise ValueError('action count mismatch')
            success = bool(data['success'])
            expected = np.zeros_like(data['rewards'])
            if expected.shape != (count, 10):
                raise ValueError('invalid reward shape')
            if success:
                expected[-1, lengths[-1] - 1] = 1
            np.testing.assert_array_equal(data['rewards'], expected)
            expected_terminal = np.zeros(count, dtype=bool)
            expected_terminal[-1] = True
            np.testing.assert_array_equal(data['finite_horizon_terminal'], expected_terminal)
            if not success and int(data['final_steps']) < int(data['task_limit']):
                raise ValueError('interruption cannot be a failure label')
            if seed != metadata['seed'] or success != metadata['success']:
                raise ValueError('metadata mismatch')
            results = list((run / 'eval' / task).glob(f"episode{metadata['index']:03d}_seed{seed}_*.json"))
            if len(results) != 1:
                raise ValueError('missing or ambiguous actual-seed evaluation result')
            result = json.loads(results[0].read_text())
            if result['seed'] != seed or result['success'] != success or result['steps'] != int(data['final_steps']):
                raise ValueError('official result mismatch')
        rows.append({'seed': seed, 'success': success, 'replans': count,
                     'file': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    if len(rows) != provenance['episodes']:
        raise ValueError('episode cap/count mismatch')
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runs', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = [row for run in args.runs for row in validate_run(run)]
    if len({row['seed'] for row in rows}) != len(rows):
        raise ValueError('duplicate actual accepted seeds')
    if args.output.exists():
        raise FileExistsError(args.output)
    report = {'valid': True, 'episodes': rows, 'count': len(rows),
              'successes': sum(row['success'] for row in rows),
              'failures': sum(not row['success'] for row in rows)}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'episodes'}))
