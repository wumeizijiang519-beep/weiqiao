"""Measure signal attenuation and chunk-weight bias without training a critic."""
import argparse
import json
from pathlib import Path
import statistics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gamma', type=float, default=0.99)
    args = parser.parse_args()
    if not 0 < args.gamma <= 1:
        raise ValueError('gamma must be in (0,1]')
    source = json.loads(args.audit.read_text())
    if source.get('valid') is not True:
        raise ValueError('input trajectory audit must pass')
    partitions = {}
    for shard in source['shards']:
        files = sorted((Path(shard['path']) / 'trajectories').glob('trajectory_*.json'))
        if len(files) != shard['observed_episodes']:
            raise ValueError('trajectory metadata count mismatch')
        partition = partitions.setdefault(shard['task_config'], [])
        for file in files:
            row = json.loads(file.read_text())
            if row['final_steps'] < 1 or row['replans'] < 1:
                raise ValueError('invalid episode duration')
            partition.append(row)
    report = {'gamma_per_action_step': args.gamma, 'partitions': {},
              'interpretation': 'Counterfactual target-scale diagnostic only; '
              'does not assert UNITAS was trained, or demonstrate QGF gain.'}
    for name, rows in partitions.items():
        successful = [row for row in rows if row['success']]
        failures = [row for row in rows if not row['success']]
        total_chunks = sum(row['replans'] for row in rows)
        factors = [args.gamma ** (row['final_steps'] - 1) for row in successful]
        report['partitions'][name] = {
            'episodes': len(rows), 'failures': len(failures),
            'failure_episode_fraction': len(failures) / len(rows),
            'failure_chunk_fraction': sum(row['replans'] for row in failures) / total_chunks,
            'total_chunks': total_chunks,
            'success_terminal_reward_weight_from_start': {
                'min': min(factors) if factors else None,
                'median': statistics.median(factors) if factors else None,
                'max': max(factors) if factors else None},
            'finite_horizon_gamma1_success_weight': 1.0,
            'note': 'Failure imbalance remains; no training admission is implied.'}
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
