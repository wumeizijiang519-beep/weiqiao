"""Audit genuine executed random-candidate actions, not invented failure labels."""
import argparse
import json
from pathlib import Path
import numpy as np
from exploration_contract import validate_commit
from validate_transitions import validate_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    rows = validate_run(args.run)
    provenance = json.loads((args.run / 'provenance.json').read_text())
    start = provenance['seed_start']
    stop = provenance.get('candidate_stop_exclusive', start + 1)
    if len(rows) != 1 or not start <= rows[0]['seed'] < stop:
        raise ValueError('engineering smoke outside preregistered scene window')
    attempts = [json.loads(line) for line in (args.run / 'trajectories' / 'feasibility_attempts.jsonl').read_text().splitlines()]
    valid = [r['seed'] for r in attempts if r.get('valid')]
    if valid != [rows[0]['seed']]:
        raise ValueError('must use the first and only expert-feasible scene')
    records = [json.loads(line) for line in (args.run / 'selection.jsonl').read_text().splitlines()]
    with np.load(rows[0]['file'], allow_pickle=False) as data:
        if len(records) != len(data['action_chunks']):
            raise ValueError('selection/transition count mismatch')
        for record, executed in zip(records, data['action_chunks'], strict=True):
            if record['reward_used_for_selection'] or record['candidate_q'] is not None:
                raise ValueError('selection contract violation')
            validate_commit(np.asarray(record['candidate_actions'], np.float32), record['selected_index'], executed)
    if records[0]['candidate0_native_initial_max_error'] is None or records[0]['candidate0_native_initial_max_error'] > 1e-6:
        raise ValueError('native candidate0 parity absent')
    report = {'valid': True, 'engineering_only': True, 'episodes': rows,
              'replans': len(records), 'selected_counts': {str(i): sum(r['selected_index'] == i for r in records) for i in range(4)},
              'max_commit_error': max(r['commit_max_error'] for r in records),
              'native_initial_error': records[0]['candidate0_native_initial_max_error'],
              'mean_replan_seconds': float(np.mean([r['latency_seconds'] for r in records]))}
    path = args.run / 'audit.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
