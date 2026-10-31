"""Publish immutable feature blocks; copying pilot artifacts never re-encodes them."""

import json
from pathlib import Path
import shutil

import numpy as np

from corpus_reader import sha


def validate_block(path, record, entry, dimension):
    if record['file'] != entry['episode_id'] + '.npz':
        raise ValueError('Feature block filename differs from episode identity')
    if record['episode_id'] != entry['episode_id'] or record['summary_sha256'] != entry['summary_sha256']:
        raise ValueError('Feature block population/summary mismatch')
    if sha(path) != record['sha256']:
        raise ValueError('Feature block hash changed')
    with np.load(path, allow_pickle=False) as data:
        if data.files != ['current_features']:
            raise ValueError('Unexpected feature block fields')
        value = data['current_features']
        if (value.shape != (entry['replans'] + 1, dimension) or value.dtype != np.float32
                or not np.isfinite(value).all()):
            raise ValueError('Finite R+1 feature contract failed')
    if len(record['observation_file_sha256']) != entry['replans'] + 1:
        raise ValueError('Feature observation provenance incomplete')


def inherit_pilot(run, pilot, population, dimension):
    records = pilot['episodes']
    if [row['episode_id'] for row in records] != ['train_0000', 'train_0001']:
        raise ValueError('Pilot episode population changed')
    destination = Path(run) / 'blocks'
    destination.mkdir()
    inherited = []
    for row in records:
        source = Path(pilot['run_directory']) / 'blocks' / row['file']
        validate_block(source, row, population[row['episode_id']], dimension)
        target = destination / row['file']
        if target.exists():
            raise ValueError('Pilot feature target already exists')
        shutil.copyfile(source, target)
        if sha(target) != row['sha256']:
            raise ValueError('Pilot copy not byte-identical')
        with (destination / (row['episode_id'] + '.json')).open('x') as stream:
            json.dump({**row, 'inherited_from': str(source), 'reencoded': False}, stream, indent=2)
        inherited.append(row)
    return inherited


def publish_index(run, records, population, dimension, dataset_sha, encoder_report, encoder_sha):
    run = Path(run)
    if (len(records) != 288 or len({row['episode_id'] for row in records}) != 288
            or {row['episode_id'] for row in records} != set(population)):
        raise ValueError('Feature union is not exactly the fixed288')
    if (run / 'INDEX.json').exists():
        raise ValueError('Never overwrite frozen full feature index')
    for row in records:
        validate_block(run / 'blocks' / row['file'], row, population[row['episode_id']], dimension)
    if sha(encoder_report) != encoder_sha:
        raise ValueError('Encoder report changed')
    shutil.copyfile(encoder_report, run / 'ENCODER_REPORT.json')
    index = dict(status='CURRENT_ONLY_CORPUS_FEATURES_COMPLETE', dataset_result_sha256=dataset_sha,
                 encoder_report='ENCODER_REPORT.json', encoder_report_sha256=encoder_sha,
                 episodes=[{**row, 'file': 'blocks/' + row['file']}
                           for row in sorted(records, key=lambda r: r['episode_id'])],
                 pilot_blocks_inherited_without_reencoding=2, newly_encoded_episodes=286,
                 feature_dimension=dimension, critic_fit=False)
    with (run / 'INDEX.json').open('x') as stream:
        json.dump(index, stream, indent=2)
    (run / 'INDEX_SHA256.txt').write_text(sha(run / 'INDEX.json') + '\n')
    return index
