"""Current-observation filesystem encoder preparation, never a rollout or fit."""

import json
import hashlib
from pathlib import Path
import time

import numpy as np

from corpus_reader import checked_json, sha


OBS_KEYS = ('agentview_image', 'robot0_eye_in_hand_image', 'robot0_eef_pos',
            'robot0_eef_quat', 'robot0_gripper_qpos')


def encode_episode(entry, encoder, *, synchronize=lambda: None):
    """The encoder callback only receives current sensors/task/known remaining."""
    folder = Path(entry['episode_directory'])
    summary = checked_json(folder / 'summary.json', entry['summary_sha256'])
    count = int(entry['replans'])
    if (summary['episode_id'] != entry['episode_id'] or summary['replans'] != count
            or len(summary['transitions']) != count or count < 0):
        raise ValueError('Certified episode/transition inventory differs')
    if not (folder / 'EPISODE_COMPLETE').exists():
        raise ValueError('Partial episode is not eligible for encoding')
    config = json.loads((folder / 'runtime_config.json').read_text())
    description = config['task_description']
    if not isinstance(description, str) or not description:
        raise ValueError('Missing task instruction')
    files = sorted(folder.glob('observation_*.npz'))
    if len(files) != count + 1:
        raise ValueError('Expected exactly R+1 measured observations')
    remaining = 700
    features, hashes, timings = [], [], []
    for number in range(count + 1):
        path = folder / f'observation_{number:04d}.npz'
        digest = sha(path)
        with np.load(path, allow_pickle=False) as data:
            observation = {key: data[key].copy() for key in OBS_KEYS}
        if not all(np.isfinite(value).all() for value in observation.values()):
            raise ValueError('Nonfinite measured observation')
        before = {key: (value.dtype.str, value.shape, hashlib.sha256(value.tobytes()).hexdigest())
                  for key, value in observation.items()}
        synchronize()
        started = time.perf_counter()
        value = np.asarray(encoder(observation, description, remaining))
        synchronize()
        after = {key: (value.dtype.str, value.shape, hashlib.sha256(value.tobytes()).hexdigest())
                 for key, value in observation.items()}
        if before != after:
            raise ValueError('Encoder mutated current measured sensors')
        timings.append(time.perf_counter() - started)
        if (value.ndim != 1 or value.dtype != np.float32 or not value.size
                or not np.isfinite(value).all()
                or (features and value.shape != features[0].shape)):
            raise ValueError('Invalid current-only feature vector')
        if sha(path) != digest:
            raise ValueError('Measured input file changed during encoding')
        features.append(value.copy())
        hashes.append(digest)
        if number < count:
            transition = folder / f'transition_{number:04d}/transition.npz'
            if sha(transition) != summary['transitions'][number]['transition_sha256']:
                raise ValueError('Previous actual feedback archive changed')
            with np.load(transition, allow_pickle=False) as data:
                before, actual, after = (int(data[key]) for key in
                                         ('remaining_before', 'actual_length', 'remaining_after'))
            if before != remaining or not 1 <= actual <= min(10, remaining) or after != remaining - actual:
                raise ValueError('Known remaining-horizon continuity failed')
            remaining = after
    return np.stack(features), dict(episode_id=entry['episode_id'],
        observation_file_sha256=hashes, observation_count=count + 1,
        encode_seconds=timings, zero_transition_episode=count == 0,
        runtime_config_sha256=sha(folder / 'runtime_config.json'))


def persist_episode(directory, entry, encoder, *, synchronize=lambda: None):
    """Write one immutable R+1 block plus provenance; no silent resume/re-encoding."""
    directory = Path(directory)
    name = entry['episode_id']
    if not name.startswith('train_') or not name[6:].isdigit() or len(name) != 10:
        raise ValueError('Unregistered training episode name')
    path, receipt = directory / (name + '.npz'), directory / (name + '.json')
    if path.exists() or receipt.exists():
        raise ValueError('Feature block exists; reconcile before any retry')
    values, record = encode_episode(entry, encoder, synchronize=synchronize)
    directory.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as output:
        np.savez_compressed(output, current_features=values)
    record.update(file=path.name, sha256=sha(path), feature_dimension=values.shape[1],
                  summary_sha256=entry['summary_sha256'],
                  source_sha256=sha(Path(__file__)))
    with receipt.open('x') as output:
        json.dump(record, output, indent=2)
    return record
