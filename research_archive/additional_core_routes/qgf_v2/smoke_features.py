"""Compare batched and current-observation feature paths on a real smoke."""
import argparse
import json
from pathlib import Path
import numpy as np
from features import encode_states

parser = argparse.ArgumentParser()
parser.add_argument('--episode', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
with np.load(args.episode, allow_pickle=False) as loaded:
    data = {key: loaded[key] for key in loaded.files}
batch = encode_states(data)
single = []
steps = np.append(data['replan_steps'], data['final_steps'])
for index in range(len(batch)):
    frame = {key: data[key][index:index + 1] for key in
             ('head_rgb', 'left_rgb', 'right_rgb', 'joint_positions', 'tcp_pose')}
    frame.update(action_chunks=np.empty((0, 10, 16), np.float32),
                 replan_steps=np.array([], np.int32), final_steps=steps[index],
                 task_limit=data['task_limit'])
    single.append(encode_states(frame)[0])
error = float(np.abs(batch - np.asarray(single)).max())
report = {'feature_source': 'fixed_rgb16patch_statistics_not_WAM_hidden',
          'episode': str(args.episode), 'observations': len(batch), 'state_dim': 701,
          'batch_vs_current_frame_max_error': error,
          'finite': bool(np.isfinite(batch).all()),
          'passed': bool(error == 0 and np.isfinite(batch).all()),
          'scope': 'feature computation parity, not online policy efficacy'}
if args.output.exists():
    raise FileExistsError(args.output)
args.output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
if not report['passed']:
    raise SystemExit(1)
