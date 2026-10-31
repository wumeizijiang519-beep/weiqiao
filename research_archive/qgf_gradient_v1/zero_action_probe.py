"""Real WAM integration gate using one retained observation, never its reward."""

import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import torch
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate
from omegaconf import OmegaConf

from core import GuidanceConfig, GuidedScheduler, native_support_basis
from experiments.libero.eval_libero_single import (
    _predict_action_chunk, maybe_compile_action_inference,
)
from simplewam.datasets.lerobot.utils.normalizer import load_dataset_stats_from_json
from simplewam.utils.pytorch_utils import set_global_seed


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
SOURCE = ROOT / 'backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a'
RUN = Path(os.environ['QGF_RUN'])
OBS_PATH = ROOT / 'runs/simplewam_intervention_train32_v1/shard0/episode_0/transition_0000.npz'
SUMMARY = OBS_PATH.parent / 'summary.json'
CHECKPOINT = ROOT / 'checkpoints/Simple-WAM/simplewam_checkpoints/libero_joint_2cam224_1e-4.pt'
STATS = ROOT / 'checkpoints/Simple-WAM/simplewam_checkpoints/libero_dataset_stats.json'
EXPECTED = {
    'src/simplewam/models/wan22/fastwam_joint.py':
        '39daa220435d3068b9db728b45241b6054d2f4ba7cde3694843b88501cd23072',
    'src/simplewam/models/wan22/schedulers/scheduler_continuous.py':
        '09389fbbf2f5a62434c08fdc2c55694d20e6ffd054df1cc63e50b924c1cc9dae',
}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda: file.read(16 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    start = time.perf_counter()
    for name, expected in EXPECTED.items():
        if sha(SOURCE / name) != expected:
            raise RuntimeError('Official source fingerprint changed: ' + name)
    set_global_seed(202640001, get_worker_init_fn=False)
    checkpoint_sha = sha(CHECKPOINT)
    if checkpoint_sha != '2b1e2f36ff06e701026028402976a4174be23ab48469289d01c93ce541b21d66':
        raise RuntimeError('Frozen checkpoint SHA mismatch')
    OmegaConf.register_new_resolver('eval', eval, replace=True)
    OmegaConf.register_new_resolver('max', max, replace=True)
    OmegaConf.register_new_resolver('split', lambda s, idx: s.split('/')[int(idx)], replace=True)
    with initialize_config_dir(version_base='1.3', config_dir=str(SOURCE / 'configs')):
        cfg = compose(config_name='sim_libero', overrides=[
            'task=libero_joint_2cam224_1e-4', f'ckpt={CHECKPOINT}', 'seed=10000',
            f'EVALUATION.output_dir={RUN}',
            f'EVALUATION.dataset_stats_path={STATS}', 'EVALUATION.num_inference_steps=10',
            'EVALUATION.binarize_gripper=true', 'EVALUATION.freeze_future_video_noise=true',
            'EVALUATION.torch_compile_action=true', 'EVALUATION.offload_text_encoder=true',
        ])
    # Hydra compose has no running Hydra job. Preserve training-only unresolved
    # interpolations instead of forcing irrelevant hydra:runtime lookups.
    (RUN / 'composed_config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=False))
    print('Configuration saved; constructing official model', flush=True)
    model = instantiate(cfg.model, model_dtype=torch.bfloat16, device='cpu')
    payload = torch.load(CHECKPOINT, map_location='cpu', weights_only=False)
    incompatible = model.mot.load_state_dict(payload['mot'], strict=False)
    if incompatible.missing_keys or incompatible.unexpected_keys:
        raise RuntimeError('Checkpoint accounting is not exact')
    model.proprio_encoder.load_state_dict(payload['proprio_encoder'], strict=True)
    del payload
    print('Checkpoint strict accounting passed', flush=True)
    model.requires_grad_(False)
    torch.cuda.reset_peak_memory_stats()
    model = model.to('cuda').eval()
    maybe_compile_action_inference(model, cfg)
    processor = instantiate(cfg.data.train.processor).eval()
    processor.set_normalizer_from_stats(load_dataset_stats_from_json(str(STATS)))
    with np.load(OBS_PATH, allow_pickle=False) as data:
        obs = {key.removeprefix('current_'): data[key].copy()
               for key in data.files if key.startswith('current_')}
    description = json.loads(SUMMARY.read_text())['task_description']
    before_obs = {key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in obs.items()}
    native_scheduler = model.infer_action_scheduler
    cache, arrays, records = {}, {}, []

    def predict(name, seed, wrapper=None):
        model.infer_action_scheduler = native_scheduler if wrapper is None else wrapper
        cfg.seed = seed
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        try:
            action, _, _, _, _, _ = _predict_action_chunk(
                obs, description, model, processor, cfg, action_horizon=32,
                input_h=224, input_w=448, model_device='cuda',
                profile_action_chunk_time=True, prompt_cache=cache,
            )
            torch.cuda.synchronize()
            action = np.asarray(action, dtype=np.float32)
            arrays[name] = action
            record = {'name': name, 'seed': seed, 'seconds': time.perf_counter() - t0}
            if wrapper is not None:
                arrays[name + '_normalized'] = wrapper.final_sample.numpy()[0]
                record.update(trace=wrapper.trace, steps=wrapper.index,
                              explicit_correction_rms=float(wrapper.used_rms.max()))
            records.append(record)
            with (RUN / 'requests.jsonl').open('a') as output:
                output.write(json.dumps(record) + '\n')
            np.savez_compressed(RUN / 'partial_arrays.npz', **arrays)
            print(name, record['seconds'], flush=True)
            return action
        finally:
            model.infer_action_scheduler = native_scheduler

    predict('official', 10000)
    zero_cfg = GuidanceConfig(weight=0, projected=False)
    predict('w0', 10000, GuidedScheduler(native_scheduler, zero_cfg))
    for i, seed in enumerate((11000, 12000, 13000), start=1):
        predict(f'bank{i}', seed, GuidedScheduler(native_scheduler, zero_cfg))
    bank = torch.from_numpy(np.stack([arrays[name + '_normalized']
                                    for name in ('w0', 'bank1', 'bank2', 'bank3')])).to('cuda')
    basis = native_support_basis(bank, 10, 6)
    if basis.shape[1] == 0:
        raise RuntimeError('Native prefix support has rank zero')
    direction = basis[:, 0].reshape(1, 10, 6).detach()
    critics = tuple((lambda a, scale=scale: scale * (a[:, :, :6] * direction).sum((1, 2)))
                    for scale in (.8, 1., 1.2))
    for name, projected in (('vanilla_toy', False), ('supported_toy', True), ('supported_repeat', True)):
        wrapper = GuidedScheduler(native_scheduler, GuidanceConfig(weight=.5, projected=projected),
                                  critics, basis)
        predict(name, 10000, wrapper)
    predict('official_after', 10000)
    w0_error = float(np.max(np.abs(arrays['official'] - arrays['w0'])))
    restore_error = float(np.max(np.abs(arrays['official'] - arrays['official_after'])))
    repeat_error = float(np.max(np.abs(arrays['supported_toy'] - arrays['supported_repeat'])))
    active = [x for row in records for x in row.get('trace', []) if x['active']]
    checks = {
        'w0_exact_native_lte_1e6': w0_error <= 1e-6,
        'restore_exact_native_lte_1e6': restore_error <= 1e-6,
        'guided_repeat_lte_1e6': repeat_error <= 1e-6,
        'all_native_shapes': all(list(a.shape) == [32, 7] for a in arrays.values()),
        'all_finite': all(np.isfinite(a).all() for a in arrays.values()),
        'binary_gripper': all(np.isin(a[:, -1], [-1., 1.]).all()
                              for name, a in arrays.items() if not name.endswith('_normalized')),
        'ten_steps_per_wrapped_call': all(row.get('steps', 10) == 10 for row in records),
        'positive_local_gradient_correction': bool(active) and
            all(x['gradient_dot_correction'] >= -1e-7 for x in active) and
            any(x['gradient_dot_correction'] > 0 for x in active),
        'explicit_suffix_and_gripper_step_correction_zero': all(
            x['suffix_step_error'] == 0 and x['gripper_step_error'] == 0 for x in active),
        'explicit_correction_budget': all(row.get('explicit_correction_rms', 0) <= .050001 for row in records),
        'nonzero_guidance_path': bool(np.max(np.abs(arrays['supported_toy_normalized']
                                                   - arrays['w0_normalized'])) > 0),
        'no_actor_parameter_gradients': all(p.grad is None for p in model.parameters()),
        'input_observation_unchanged': before_obs == {
            key: hashlib.sha256(value.tobytes()).hexdigest() for key, value in obs.items()},
        'official_source_unchanged': all(sha(SOURCE / key) == value for key, value in EXPECTED.items()),
    }
    report = {
        'status': 'ENGINEERING_PASS' if all(checks.values()) else 'ENGINEERING_FAIL',
        'scope': 'SYNTHETIC_LINEAR_CRITICS_NO_RL_FIT_NO_ROLLOUT_NO_EFFICACY_CLAIM',
        'model_actions_executed': 0, 'environment_instances_created': 0,
        'observation': str(OBS_PATH), 'observation_file_sha256': sha(OBS_PATH),
        'checkpoint_sha256': checkpoint_sha, 'stats_sha256': sha(STATS),
        'source_sha256': EXPECTED, 'parameter_count': sum(p.numel() for p in model.parameters()),
        'missing_keys': [], 'unexpected_keys': [], 'proprio_strict': True,
        'support_rank': basis.shape[1], 'w0_max_error': w0_error,
        'restoration_max_error': restore_error, 'guided_repeat_max_error': repeat_error,
        'checks': {key: bool(value) for key, value in checks.items()}, 'requests': records,
        'peak_cuda_bytes': torch.cuda.max_memory_allocated(),
        'wall_seconds': time.perf_counter() - start,
        'limitations': ['Toy critics are not learned Q functions.',
                       'Projection is geometric, not a behavioral-support guarantee.',
                       'Explicit correction budget does not bound final policy displacement.',
                       'The official fast mode freezes future video noise; it is not a learned action-conditioned rollout.'],
    }
    np.savez_compressed(RUN / 'arrays.npz', **arrays, support_basis=basis.cpu().numpy())
    (RUN / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({key: value for key, value in report.items() if key != 'requests'}, indent=2), flush=True)
    if not all(checks.values()):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
