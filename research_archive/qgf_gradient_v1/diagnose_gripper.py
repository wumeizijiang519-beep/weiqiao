"""Zero-environment replay of the exact stopped training observation."""

import json
import os
from pathlib import Path
import time

import numpy as np
import torch

from core import GuidanceConfig, GuidedScheduler
from data_contract import array_hash, load_rng, restore_rng, rng_hash
from wam_runtime import ROOT, file_sha, load_wam


def main():
    from experiments.libero.eval_libero_single import _predict_action_chunk

    run = Path(os.environ['QGF_DIAGNOSTIC_RUN'])
    if run.exists():
        raise RuntimeError('Never overwrite a diagnostic')
    run.mkdir()
    source = ROOT / 'runs/qgf_gradient_training288_v1_shard0/train_0030'
    observation_path = source / 'observation_0021.npz'
    boundary = source / 'transition_0021'
    config = json.loads((source / 'runtime_config.json').read_text())
    selected = json.loads((boundary / 'selection.json').read_text())
    with np.load(observation_path, allow_pickle=False) as loaded:
        obs = {key: loaded[key].copy() for key in loaded.files}
    rng = load_rng(boundary / 'rng_before.npz')
    started = time.perf_counter()
    cfg, model, processor = load_wam(run)
    scheduler = model.infer_action_scheduler
    cache, bank, raw, times = {}, [], [], []
    for seed in [10000, 11000, 12000, 13000]:
        restore_rng(rng)
        cfg.seed = seed
        wrapper = GuidedScheduler(scheduler, GuidanceConfig(weight=0, projected=False))
        model.infer_action_scheduler = wrapper
        t0 = time.perf_counter()
        try:
            native, *_ = _predict_action_chunk(
                obs, config['task_description'], model, processor, cfg, action_horizon=32,
                input_h=224, input_w=448, model_device='cuda',
                profile_action_chunk_time=True, prompt_cache=cache)
            torch.cuda.synchronize()
            bank.append(np.asarray(native, dtype=np.float32).copy())
            raw.append(wrapper.final_sample.numpy()[0].copy())
            times.append(time.perf_counter() - t0)
            np.savez_compressed(run / 'partial_bank.npz', native=np.stack(bank), raw=np.stack(raw))
        finally:
            model.infer_action_scheduler = scheduler
    bank, raw = np.stack(bank), np.stack(raw)
    context = {key: array_hash(value.detach().cpu().float().numpy()) for key, value in cache.items()}
    bad_indices = np.argwhere(~np.isin(bank[..., -1], [-1., 1.]))
    key = processor.shape_meta['action'][0]['key']
    normalizer = processor.normalizer.normalizers['action'][key]
    scale = normalizer.scale.detach().cpu().float().numpy()
    offset = normalizer.offset.detach().cpu().float().numpy()
    before_binary = (raw - offset) / scale
    violations = [{'candidate': int(i), 'step': int(j), 'native_gripper': float(bank[i, j, -1]),
                   'raw_normalized_gripper': float(raw[i, j, -1]),
                   'dataset_gripper_before_sign': float(before_binary[i, j, -1])}
                  for i, j in bad_indices]
    finite = bool(np.isfinite(bank).all() and np.isfinite(raw).all())
    result = {
        'status': 'REPRODUCED_NATIVE_GRIPPER_CONTRACT_FAILURE' if finite and len(violations)
        else ('NOT_REPRODUCED' if finite else 'NONFINITE_NATIVE_ACTION'),
        'scope': 'Exact saved observation/native policy replay; no environment or action execution.',
        'source_episode': str(source), 'source_boundary': 21,
        'observation_sha256': file_sha(observation_path), 'boundary_rng_hash': rng_hash(rng),
        'description': config['task_description'], 'selected_index_original': selected['selected_index'],
        'original_bank_was_not_saved': True,
        'context_matches_original': context == selected['prompt_context_hashes'],
        'bank_shape': list(bank.shape), 'all_finite': finite,
        'native_gripper_unique': np.unique(bank[..., -1]).tolist(), 'violations': violations,
        'latencies_seconds': times, 'wall_seconds': time.perf_counter() - started,
        'policy_actions_executed': 0, 'environment_instances_created': 0,
        'peak_cuda_bytes': torch.cuda.max_memory_allocated(),
        'limitation': 'Cross-process replay is a reproduction; original failed bank was not retained by the old exception path.'
    }
    np.savez_compressed(run / 'bank.npz', native=bank, raw=raw, action_scale=scale, action_offset=offset)
    (run / 'REPORT.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    (run / 'DIAGNOSTIC_COMPLETE').touch()
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
