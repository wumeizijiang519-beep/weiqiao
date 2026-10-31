"""Zero-GPU observation I/O timing at fixed metadata positions, no encoding."""

import json
from pathlib import Path
import time

import numpy as np

from corpus_reader import certified_population, sha
from feature_corpus import OBS_KEYS


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
dataset = ROOT / 'qgf_gradient_v1/training288_v2_remaining/DATASET_RESULT.json'
digest = 'baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87'
population = certified_population(dataset, digest)
destination = ROOT / 'qgf_gradient_v1/FEATURE_IO_BENCHMARK.json'
if destination.exists():
    raise RuntimeError('I/O benchmark already frozen')
rows = []
for number in np.linspace(0, 287, 14).astype(int):
    name = f'train_{number:04d}'
    path = Path(population[name]['episode_directory']) / 'observation_0000.npz'
    started = time.perf_counter()
    before = sha(path)
    with np.load(path, allow_pickle=False) as data:
        values = {key: data[key].copy() for key in OBS_KEYS}
    if not all(np.isfinite(value).all() for value in values.values()) or sha(path) != before:
        raise RuntimeError('Read-only I/O input invalid or changed')
    rows.append(dict(episode_id=name, observation_sha256=before,
                     seconds=time.perf_counter() - started))
report = dict(status='CPU_IO_BENCHMARK_ONLY', dataset_sha256=digest, samples=rows,
              p90_seconds=float(np.quantile([row['seconds'] for row in rows], .9)),
              gpu_seconds=0, source_sha256=sha(Path(__file__)),
              caveat='Small fixed boundary sample, filesystem cache/load may differ at full scale')
destination.write_text(json.dumps(report, indent=2))
print(json.dumps(report), flush=True)
