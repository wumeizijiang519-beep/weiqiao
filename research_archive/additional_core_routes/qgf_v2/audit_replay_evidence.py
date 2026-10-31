"""Quantify preserved replay differences without changing acceptance thresholds."""
import argparse
import json
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
args = parser.parse_args()
with np.load(args.directory / 'replay_evidence.npz', allow_pickle=False) as data:
    error = np.abs(data['first_images'].astype(np.float32) - data['replay_images'].astype(np.float32))
    states = np.abs(data['first_states'] - data['replay_states'])
    report = {'joint_max_abs_error': float(states.max()),
              'rgb_mae_255_scale': float(error.mean()),
              'rgb_max_abs_error': float(error.max()),
              'rgb_nonzero_fraction': float((error > 0).mean()),
              'rgb_abs_error_gt10_fraction': float((error > 10).mean()),
              'note': 'Descriptive diagnostics only. Original exact-RGB gate remains unchanged.'}
output = args.directory / 'difference_diagnostics.json'
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
