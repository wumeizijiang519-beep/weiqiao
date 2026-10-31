"""Independent zero-GPU feature/actual-feedback reconciliation and tensor export."""

import argparse
import json
from pathlib import Path
import time
import traceback

import numpy as np

from corpus_reader import certified_population, checked_json, load_admitted_episode, sha


ARRAY_KEYS = ('observation', 'next_observation', 'action', 'bank', 'mask', 'rewards',
              'executed_steps', 'planned_steps', 'remaining_before', 'selected_index',
              'terminal', 'mc_return')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    for name, digest in reg['source_sha256'].items():
        if sha(Path(__file__).parent / name) != digest:
            raise RuntimeError('CPU feature audit source changed')
    population = certified_population(reg['dataset'], reg['dataset_sha256'])
    feature_root = Path(reg['feature_root'])
    index = checked_json(feature_root / 'INDEX.json', reg['index_sha256'])
    if index['status'] != 'CURRENT_ONLY_CORPUS_FEATURES_COMPLETE':
        raise RuntimeError('Feature extraction incomplete')
    run = Path(reg['run_directory'])
    run.mkdir()
    started = time.monotonic()
    try:
        pieces, ledger, offset = [], [], 0
        for name in sorted(population):
            arrays, meta = load_admitted_episode(reg['dataset'], reg['dataset_sha256'],
                                                 feature_root, reg['index_sha256'], name)
            count = meta['fitting_rows']
            meta['transition_indices'] = list(range(offset, offset + count))
            ledger.append(meta)
            if arrays is not None:
                pieces.append(arrays)
                offset += count
            print(name, count, offset, flush=True)
        if len(ledger) != 288 or len({row['episode_id'] for row in ledger}) != 288:
            raise RuntimeError('Scientific episode denominator changed')
        if not pieces:
            raise RuntimeError('No measured actions to fit; do not invent transitions')
        corpus = {key: np.concatenate([piece[key] for piece in pieces]) for key in ARRAY_KEYS}
        np.savez_compressed(run / 'CORPUS.npz', **corpus)
        corpus_meta = dict(episodes=ledger, dataset_result_sha256=reg['dataset_sha256'],
                           feature_index_sha256=reg['index_sha256'],
                           nonempty_fitting_episodes=sum(row['fitting_rows'] > 0 for row in ledger),
                           scientific_episodes=288, transitions=offset,
                           feature_dimension=corpus['observation'].shape[1])
        (run / 'CORPUS_METADATA.json').write_text(json.dumps(corpus_meta, indent=2))
        report = dict(status='FULL_FEATURE_CORPUS_INDEPENDENT_AUDIT_PASS',
                      dataset_result_sha256=reg['dataset_sha256'], index_sha256=reg['index_sha256'],
                      registration_sha256=sha(args.registration),
                      scientific_episodes=288, fitting_episodes=corpus_meta['nonempty_fitting_episodes'],
                      transitions=offset, corpus_sha256=sha(run / 'CORPUS.npz'),
                      metadata_sha256=sha(run / 'CORPUS_METADATA.json'),
                      zero_transition_episodes=288-corpus_meta['nonempty_fitting_episodes'],
                      wall_seconds=time.monotonic()-started, gpu_seconds=0, critic_fit=False)
        (run / 'REPORT.json').write_text(json.dumps(report, indent=2))
        (run / 'FEATURE_CORPUS_AUDIT_PASS').touch()
        print(json.dumps(report), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
