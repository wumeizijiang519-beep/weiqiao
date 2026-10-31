"""Independent merged-episode and immutable-prefix audit, after clean process exit."""

import argparse
import json
from pathlib import Path

import numpy as np

from audit_collection_v2 import audit_episode
from data_contract import OBS_KEYS, load_rng, observation_hash, rng_hash
from wam_runtime import ROOT, file_sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run = args.run
    if (run / 'process_exit_code').read_text().strip() != '0' or not (run / 'COLLECTION_COMPLETE').exists():
        raise RuntimeError('Not a clean completed collection')
    registration = json.loads((run / 'registration.json').read_text())
    if registration['episode_ids'] != ['train_0030'] or registration['resume_episode_ids'] != ['train_0030']:
        raise RuntimeError('Not the registered single partial entry')
    folder = run / 'train_0030'
    provenance = json.loads((folder / 'inherited_prefix.json').read_text())
    original = Path(provenance['source'])
    for name, digest in provenance['sha256'].items():
        if file_sha(original / name) != digest or file_sha(folder / name) != digest:
            raise RuntimeError('Original or copied inherited evidence changed: ' + name)
    entry = json.loads((original / 'config.json').read_text())
    report = audit_episode(folder, entry)
    old_selection = json.loads((original / 'transition_0021/selection.json').read_text())
    new_selection = json.loads((folder / 'transition_0021/selection.json').read_text())
    for key in ('before', 'after', 'selected_index', 'selection_seed', 'prompt_context_hashes'):
        if old_selection[key] != new_selection[key]:
            raise RuntimeError('Interrupted selection changed: ' + key)
    if new_selection['candidate0_replay_error'] is None or new_selection['candidate0_replay_error'] > 1e-6:
        raise RuntimeError('First resumed candidate0 replay missing/failed')
    if rng_hash(load_rng(original / 'transition_0021/rng_before.npz')) != rng_hash(
            load_rng(folder / 'transition_0021/rng_before.npz')):
        raise RuntimeError('Interrupted caller RNG changed')
    with np.load(original / 'observation_0021.npz', allow_pickle=False) as saved:
        original_sensor = {key: saved[key].copy() for key in OBS_KEYS}
    with np.load(folder / 'transition_0021/transition.npz', allow_pickle=False) as saved:
        if observation_hash(original_sensor) != observation_hash(
                {key: saved['current_' + key] for key in OBS_KEYS}):
            raise RuntimeError('Actual first resumed model input differs from retained sensor')
    gate = ROOT / 'runs/qgf_gradient_checkpoint_gate_v3/REPORT.json'
    if file_sha(gate) != registration['checkpoint_gate_sha256']:
        raise RuntimeError('Registered recovery gate changed')
    if file_sha(original / 'rollout.mp4') != file_sha(folder / 'archived_partial_rollout.mp4'):
        raise RuntimeError('Original partial video not preserved')
    result = {'status': 'RESUMED_EPISODE_INDEPENDENT_AUDIT_PASS', 'episode': report,
              'original_prefix_transitions': 21, 'original_prefix_steps': 210,
              'new_policy_steps': report['model_steps'] - 210,
              'cohort_entries_completed': 1, 'completed_entries_resampled': 0,
              'v2_raw_raster_gate': 'FAILED; not relabelled',
              'recovery_contract': 'V3 physical history plus original measured sensor snapshot',
              'video_prefix': 'reconstructed; original preserved separately',
              'method_efficacy_conclusion': None, 'report_sha256': file_sha(run / 'report.json')}
    result['audit_source_sha256'] = file_sha(Path(__file__))
    (run / 'RESUME_AUDIT.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    (run / 'RESUME_AUDIT_PASS').touch()
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
