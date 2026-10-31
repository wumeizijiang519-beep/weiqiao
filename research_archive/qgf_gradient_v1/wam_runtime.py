"""Frozen official model/config loading shared by the prospective collectors."""

import hashlib
from pathlib import Path

import torch
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate
from omegaconf import OmegaConf

ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
SOURCE = ROOT / 'backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a'
CHECKPOINT = ROOT / 'checkpoints/Simple-WAM/simplewam_checkpoints/libero_joint_2cam224_1e-4.pt'
STATS = ROOT / 'checkpoints/Simple-WAM/simplewam_checkpoints/libero_dataset_stats.json'
CHECKPOINT_SHA = '2b1e2f36ff06e701026028402976a4174be23ab48469289d01c93ce541b21d66'
STATS_SHA = '6b49b1bdf37268e3f1e6e621c4d5cb03ba028f3fabff3df3c68067c0a7c91c69'
MANIFEST_SHA = '7194f02c8dba2c9ae01fddab1d0c48c169e28f6778e3926a0386dfeff0307af9'
SOURCE_HASHES = {
    'src/simplewam/models/wan22/fastwam_joint.py':
        '39daa220435d3068b9db728b45241b6054d2f4ba7cde3694843b88501cd23072',
    'src/simplewam/models/wan22/schedulers/scheduler_continuous.py':
        '09389fbbf2f5a62434c08fdc2c55694d20e6ffd054df1cc63e50b924c1cc9dae',
}


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def load_wam(run):
    # File auditing/registration must not initialize a renderer on login nodes.
    from experiments.libero.eval_libero_single import maybe_compile_action_inference
    from simplewam.datasets.lerobot.utils.normalizer import load_dataset_stats_from_json
    from simplewam.utils.pytorch_utils import set_global_seed

    for name, expected in SOURCE_HASHES.items():
        if file_sha(SOURCE / name) != expected:
            raise RuntimeError('Changed official model source: ' + name)
    if file_sha(CHECKPOINT) != CHECKPOINT_SHA or file_sha(STATS) != STATS_SHA:
        raise RuntimeError('Changed frozen asset')
    set_global_seed(202640001, get_worker_init_fn=False)
    OmegaConf.register_new_resolver('eval', eval, replace=True)
    OmegaConf.register_new_resolver('max', max, replace=True)
    OmegaConf.register_new_resolver('split', lambda s, idx: s.split('/')[int(idx)], replace=True)
    with initialize_config_dir(version_base='1.3', config_dir=str(SOURCE / 'configs')):
        cfg = compose(config_name='sim_libero', overrides=[
            'task=libero_joint_2cam224_1e-4', f'ckpt={CHECKPOINT}', 'seed=10000',
            f'EVALUATION.output_dir={run}', f'EVALUATION.dataset_stats_path={STATS}',
            'EVALUATION.num_inference_steps=10', 'EVALUATION.binarize_gripper=true',
            'EVALUATION.freeze_future_video_noise=true',
            'EVALUATION.torch_compile_action=true', 'EVALUATION.offload_text_encoder=true',
        ])
    (run / 'composed_config.yaml').write_text(OmegaConf.to_yaml(cfg, resolve=False))
    print('Constructing unchanged official WAM', flush=True)
    model = instantiate(cfg.model, model_dtype=torch.bfloat16, device='cpu')
    payload = torch.load(CHECKPOINT, map_location='cpu', weights_only=False)
    mismatch = model.mot.load_state_dict(payload['mot'], strict=False)
    if mismatch.missing_keys or mismatch.unexpected_keys:
        raise RuntimeError('Nonzero model weight mismatch')
    model.proprio_encoder.load_state_dict(payload['proprio_encoder'], strict=True)
    del payload
    model.requires_grad_(False)
    torch.cuda.reset_peak_memory_stats()
    model = model.to('cuda').eval()
    maybe_compile_action_inference(model, cfg)
    processor = instantiate(cfg.data.train.processor).eval()
    processor.set_normalizer_from_stats(load_dataset_stats_from_json(str(STATS)))
    print('Strict checkpoint accounting passed; actor frozen', flush=True)
    return cfg, model, processor
