"""Prepare current-only encoder qualification; never run before full data admission."""

import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback

import numpy as np
import torch

from data_contract import capture_rng, observation_hash, observation_payload, restore_rng, rng_hash
from features import CurrentWamFeatures
from wam_runtime import CHECKPOINT_SHA, MANIFEST_SHA, ROOT, STATS_SHA, file_sha, load_wam


def audit_order(encode, case_a, case_b, synchronize=lambda: None):
    """A-B-A replay with exact input/RNG checks and predeclared feature tolerance."""
    initial_rng = capture_rng()
    features, records = [], []
    try:
        for name, case in [('A', case_a), ('B', case_b), ('A_repeat', case_a)]:
            observation, description, remaining = case
            obs_before = observation_hash(observation_payload(observation))
            rng_before = rng_hash(capture_rng())
            synchronize()
            started = time.perf_counter()
            value = np.asarray(encode(observation, description, remaining)).copy()
            synchronize()
            elapsed = time.perf_counter() - started
            if rng_hash(capture_rng()) != rng_before:
                raise RuntimeError('Encoder changed caller Python/NumPy/Torch RNG')
            if observation_hash(observation_payload(observation)) != obs_before:
                raise RuntimeError('Encoder changed current observation')
            if value.ndim != 1 or value.dtype != np.float32 or not np.isfinite(value).all():
                raise RuntimeError('Invalid finite float32 feature vector')
            if features and value.shape != features[0].shape:
                raise RuntimeError('Encoder feature dimension changed')
            features.append(value)
            records.append({'request': name, 'observation_hash': obs_before, 'caller_rng_hash': rng_before,
                            'remaining_steps': remaining, 'seconds': elapsed})
        difference = float(np.abs(features[0] - features[2]).max())
        if difference > 1e-6:
            raise RuntimeError('Feature A-B-A replay failed; possible hidden temporal state')
        return features, {'requests': records, 'feature_repeat_max_abs_error': difference,
                          'caller_rng_exact': True, 'inputs_unchanged': True}
    finally:
        restore_rng(initial_rng)


def buffer_hashes(model):
    result = {}
    for name, value in model.named_buffers():
        raw = value.detach().contiguous().reshape(-1).view(torch.uint8).cpu().numpy()
        result[name] = {'dtype': str(value.dtype), 'shape': list(value.shape),
                        'sha256': hashlib.sha256(raw.tobytes()).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    dataset = ROOT / 'qgf_gradient_v1/training288_v2_remaining/DATASET_RESULT.json'
    digest = dataset.with_name('DATASET_RESULT_SHA256.txt').read_text().strip()
    if file_sha(dataset) != digest:
        raise RuntimeError('Qualified dataset result hash changed')
    admitted = json.loads(dataset.read_text())
    if (admitted['status'] != 'ADMIT_FOR_RL_QUALIFICATION' or admitted['episodes'] != 288
            or admitted['manifest_sha256'] != MANIFEST_SHA):
        raise RuntimeError('Full fixed corpus has not passed data qualification')
    if file_sha(ROOT / 'qgf_gradient_v1/evidence/COHORT_MANIFEST.json') != MANIFEST_SHA:
        raise RuntimeError('Frozen population changed')
    args.run.mkdir(exist_ok=False)
    try:
        entries = sorted(admitted['entries'], key=lambda row: row['episode_id'])
        cases, sources = [], []
        # Fixed endpoints in manifest order, never selected by success/difficulty.
        for entry in (entries[0], entries[-1]):
            folder = Path(entry['episode_directory'])
            obs_path = folder / 'observation_0000.npz'
            with np.load(obs_path, allow_pickle=False) as saved:
                observation = observation_payload(saved)
            description = json.loads((folder / 'runtime_config.json').read_text())['task_description']
            cases.append((observation, description, 700))
            sources.append({'episode_id': entry['episode_id'], 'observation_file_sha256': file_sha(obs_path)})
        if observation_hash(cases[0][0]) == observation_hash(cases[1][0]):
            raise RuntimeError('Fixed A/B observations are identical; no temporal-order audit')
        cfg, model, processor = load_wam(args.run)
        if any(parameter.requires_grad or parameter.grad is not None for parameter in model.parameters()):
            raise RuntimeError('WAM must be frozen with no actor gradients')
        before_buffers = buffer_hashes(model)
        encoder = CurrentWamFeatures(model, processor, cfg)
        torch.cuda.reset_peak_memory_stats()
        values, report = audit_order(encoder, *cases, synchronize=torch.cuda.synchronize)
        if buffer_hashes(model) != before_buffers:
            raise RuntimeError('Encoder changed registered model buffers')
        if any(parameter.grad is not None for parameter in model.parameters()):
            raise RuntimeError('Actor gradient created by feature audit')
        np.savez_compressed(args.run / 'features.npz', A=values[0], B=values[1], A_repeat=values[2])
        report.update(status='CURRENT_FEATURE_ENCODER_AUDIT_PASS', feature_spec=encoder.spec,
                      feature_spec_sha256=hashlib.sha256(json.dumps(encoder.spec, sort_keys=True).encode()).hexdigest(),
                      source_observations=sources, checkpoint_sha256=CHECKPOINT_SHA, stats_sha256=STATS_SHA,
                      dataset_result_sha256=digest, registered_buffers_unchanged=True,
                      peak_encoder_phase_cuda_bytes=torch.cuda.max_memory_allocated(),
                      measured_actions=0, environment_instances=0, model_inference_actions=0,
                      future_frames=0, critic_fit=False, efficacy_conclusion=None,
                      source_sha256=file_sha(Path(__file__)),
                      features_source_sha256=file_sha(Path(__file__).with_name('features.py')))
        (args.run / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        (args.run / 'ENCODER_AUDIT_PASS').touch()
        print(json.dumps(report, indent=2), flush=True)
    except BaseException:
        (args.run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
