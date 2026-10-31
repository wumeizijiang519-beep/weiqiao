"""Audit every executed intervention and transition in a bounded bulk shard."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from exploration_contract import validate_commit
from validate_transitions import validate_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--episodes', type=int, required=True)
    args = parser.parse_args()
    rows = validate_run(args.run)
    provenance = json.loads((args.run / 'provenance.json').read_text())
    if len(rows) != args.episodes or len({r['seed'] for r in rows}) != args.episodes:
        raise ValueError('exact preregistered episode count required')
    if not all(provenance['seed_start'] <= r['seed'] < provenance['seed_stop'] for r in rows):
        raise ValueError('accepted scene outside frozen window')
    records = [json.loads(line) for line in (args.run / 'selection.jsonl').read_text().splitlines()]
    cursor, selected_counts, pair_distances, latencies = 0, [0] * 4, [], []
    for row in rows:
        with np.load(row['file'], allow_pickle=False) as data:
            count = len(data['action_chunks'])
            episode_records = records[cursor:cursor + count]
            if len(episode_records) != count:
                raise ValueError('selection/transition count mismatch')
            for record, executed in zip(episode_records, data['action_chunks'], strict=True):
                if record['reward_used_for_selection'] or record['candidate_q'] is not None:
                    raise ValueError('oracle selection contract violation')
                candidates = np.asarray(record['candidate_actions'], np.float32)
                validate_commit(candidates, record['selected_index'], executed)
                selected_counts[record['selected_index']] += 1
                latencies.append(record['latency_seconds'])
                pair_distances.extend(float(np.mean(np.abs(candidates[i] - candidates[j])))
                                      for i in range(4) for j in range(i))
            cursor += count
    if cursor != len(records) or not pair_distances or max(pair_distances) == 0:
        raise ValueError('unused records or degenerate candidates')
    report = {'valid': True, 'training_only': True, 'episodes': rows,
              'successes': sum(r['success'] for r in rows),
              'failures': sum(not r['success'] for r in rows), 'replans': len(records),
              'selected_counts': selected_counts, 'max_commit_error': 0.0,
              'candidate_pair_mean_abs': float(np.mean(pair_distances)),
              'candidate_pair_p95_abs': float(np.quantile(pair_distances, .95)),
              'mean_replan_seconds': float(np.mean(latencies))}
    path = args.run / 'audit.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(report, indent=2) + '\n')
    (args.run / 'COLLECTION_COMPLETE').touch()
    print(json.dumps(report))


if __name__ == '__main__':
    main()
