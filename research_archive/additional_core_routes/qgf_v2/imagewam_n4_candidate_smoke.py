import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    imagewam = root / "backbones" / "ImageWAM"
    checkpoint = root / "checkpoints_first_tier" / "imagewam" / "libero_plus" / "model.pt"
    stats_path = checkpoint.parent / "dataset_stats.json"
    flux2 = imagewam / "third_party" / "flux2"
    flux2_model = root / "checkpoints_first_tier" / "imagewam" / "flux2" / "FLUX.2-klein-base-4B" / "flux-2-klein-base-4b.safetensors"
    ae_model = root / "checkpoints_first_tier" / "imagewam" / "flux2" / "FLUX.2-public-vae-bfl-layout" / "ae.safetensors"
    qwen_model = root / "checkpoints_first_tier" / "imagewam" / "flux2" / "Qwen3-4B"

    # The official evaluator uses local imports from its script directory.
    sys.path.insert(0, str(imagewam / "experiments" / "libero"))

    overrides = [
        "task=libero_flux2_klein_4b_base_imagewam",
        f"ckpt={checkpoint}",
        "gpu_id=0",
        "seed=10000",
        f"EVALUATION.dataset_stats_path={stats_path}",
        "EVALUATION.task_suite_name=libero_10",
        "EVALUATION.task_id=0",
        "EVALUATION.num_trials=1",
        "EVALUATION.action_horizon=16",
        "EVALUATION.replan_steps=12",
        f"model.flux2_src_path={flux2}",
        f"model.flux2_model_path={flux2_model}",
        f"model.ae_model_path={ae_model}",
        "model.variant=klein-base-4b",
        f"model.qwen3_model_spec={qwen_model}",
        "model.qwen_context_len=128",
        "model.load_text_encoder=true",
        "model.pack_proprio_after_text=true",
        "model.proprio_dim=8",
        "model.flux2_lora_config.enabled=false",
        "data.train.qwen_text_cache_format=qwen3_flux2",
    ]
    with initialize_config_dir(version_base="1.3", config_dir=str(imagewam / "configs")):
        cfg = compose(config_name="sim_libero_omnigen2", overrides=overrides)

    from experiments.libero import eval_libero_single as ev
    from experiments.libero.libero_utils import LIBERO_ENV_RESOLUTION, get_libero_dummy_action, get_libero_env
    from imagewam.datasets.lerobot.processors.imagewam_processor import ImageWAMProcessor
    from imagewam.datasets.lerobot.utils.normalizer import load_dataset_stats_from_json
    from libero.libero import benchmark

    model_cfg = ev._resolve_model_cfg(cfg)
    model = instantiate(model_cfg, model_dtype=torch.bfloat16, device="cuda")
    ev._load_model_checkpoint(model, str(checkpoint))
    model = model.to("cuda").eval()

    stats = load_dataset_stats_from_json(str(stats_path))
    processor: ImageWAMProcessor = instantiate(cfg.data.train.processor).eval()
    processor.set_normalizer_from_stats(stats)

    suite = benchmark.get_benchmark_dict()["libero_10"]()
    task = suite.get_task(0)
    initial_state = suite.get_task_init_states(0)[0]
    env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, 10000)
    env.reset()
    obs = env.set_init_state(initial_state)
    for _ in range(30):
        obs, _, _, _ = env.step(get_libero_dummy_action())

    seeds = [10000, 11000, 12000, 13000]
    chunks = []
    latencies = []
    for seed in seeds:
        cfg.seed = seed
        start = time.perf_counter()
        action, images, _ = ev._predict_action_chunk(
            obs,
            description,
            model,
            processor,
            cfg,
            action_horizon=16,
            input_w=448,
            input_h=224,
            model_device="cuda",
        )
        torch.cuda.synchronize()
        latencies.append(time.perf_counter() - start)
        chunks.append(np.asarray(action, dtype=np.float32))

    cfg.seed = seeds[0]
    repeat, _, _ = ev._predict_action_chunk(
        obs,
        description,
        model,
        processor,
        cfg,
        action_horizon=16,
        input_w=448,
        input_h=224,
        model_device="cuda",
    )
    torch.cuda.synchronize()
    chunks_array = np.stack(chunks)
    repeat = np.asarray(repeat, dtype=np.float32)

    pairwise = []
    for i in range(len(seeds)):
        for j in range(i + 1, len(seeds)):
            pairwise.append(float(np.mean(np.abs(chunks_array[i] - chunks_array[j]))))
    hashes = [hashlib.sha256(chunk.tobytes()).hexdigest() for chunk in chunks_array]
    repeat_error = float(np.max(np.abs(chunks_array[0] - repeat)))
    finite = bool(np.isfinite(chunks_array).all())
    gripper_values = chunks_array[..., -1]
    gripper_binary = bool(np.all(np.isin(gripper_values, [-1.0, 0.0, 1.0])))
    passed = bool(
        chunks_array.shape == (4, 16, 7)
        and finite
        and len(set(hashes)) == 4
        and repeat_error <= 1e-6
        and gripper_binary
        and float(np.median(pairwise)) >= 1e-4
    )

    np.savez_compressed(
        output / "candidates.npz",
        seeds=np.asarray(seeds),
        chunks=chunks_array,
        candidate0_repeat=repeat,
        agentview=np.asarray(images["image"]),
        wrist=np.asarray(images["wrist_image"]),
    )
    report = {
        "status": "PASS" if passed else "FAIL",
        "task_suite": "libero_10",
        "task_id": 0,
        "environment_seed": 10000,
        "candidate_seeds": seeds,
        "shape": list(chunks_array.shape),
        "finite": finite,
        "hashes": hashes,
        "unique_hashes": len(set(hashes)),
        "candidate0_repeat_max_abs_error": repeat_error,
        "gripper_binary": gripper_binary,
        "pairwise_mean_abs": pairwise,
        "pairwise_min": float(np.min(pairwise)),
        "pairwise_median": float(np.median(pairwise)),
        "pairwise_mean": float(np.mean(pairwise)),
        "latency_seconds": latencies,
        "cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    env.close()
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
