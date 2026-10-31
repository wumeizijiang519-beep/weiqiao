from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
from hydra import compose, initialize_config_dir
from hydra.utils import instantiate

from libero.libero import benchmark
from kairoswam.datasets.lerobot.utils.normalizer import load_dataset_stats_from_json
from experiments.libero import eval_libero_single as ev
from experiments.libero.libero_utils import close_libero_env, get_libero_dummy_action, get_libero_env


RUN = Path(os.environ["KAIROS_N4_RUN"])
CONFIG_DIR = os.environ["KAIROS_LIBERO_CONFIG_DIR"]
STATS = os.environ["DATASET_STATS_PATH"]
ENDPOINT = os.environ["MODEL_ENDPOINT"]
SEEDS = [10000, 11000, 12000, 13000]


def digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float32).tobytes()).hexdigest()


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    overrides = [
        "task=libero_uncond_2cam224_1e-4",
        "model=external_model_adapter",
        f"model.endpoint={ENDPOINT}",
        "ckpt=/nothing/to/load",
        "seed=10000",
        "gpu_id=0",
        "EVALUATION.task_suite_name=libero_mix",
        "EVALUATION.task_id=0",
        "EVALUATION.num_trials=1",
        "EVALUATION.category_value=Background Textures",
        f"EVALUATION.dataset_stats_path={STATS}",
        f"EVALUATION.output_dir={RUN / 'output'}",
        "EVALUATION.num_steps_wait=30",
        "EVALUATION.replan_steps=10",
        "EVALUATION.binarize_gripper=true",
        "EVALUATION.num_inference_steps=20",
    ]
    with initialize_config_dir(version_base="1.3", config_dir=CONFIG_DIR):
        cfg = compose(config_name="sim_libero.yaml", overrides=overrides)

    model_device = ev._resolve_eval_device(cfg)
    model_dtype = ev._mixed_precision_to_model_dtype(cfg.get("mixed_precision", "bf16"))
    model = instantiate(cfg.model, model_dtype=model_dtype, device=model_device).to(model_device).eval()
    processor = instantiate(cfg.data.train.processor).eval()
    processor.set_normalizer_from_stats(load_dataset_stats_from_json(STATS))

    action_horizon = int(cfg.data.train.num_frames) - 1
    input_h, input_w = (int(value) for value in cfg.data.train.video_size)
    task_suite = benchmark.get_benchmark_dict()["libero_mix"](
        category_value="Background Textures"
    )
    task = task_suite.get_task(0)
    initial_state = list(task_suite.get_task_init_states(0))[0]
    env, task_description = get_libero_env(task, ev.LIBERO_ENV_RESOLUTION, 10000)

    try:
        env.reset()
        obs = env.set_init_state(initial_state)
        for _ in range(30):
            obs, _, _, _ = env.step(get_libero_dummy_action())

        candidates = []
        latencies = []
        for seed in SEEDS:
            cfg.seed = seed
            started = time.perf_counter()
            chunk, _, _ = ev._predict_action_chunk(
                obs,
                task_description,
                model,
                processor,
                cfg,
                action_horizon=action_horizon,
                input_w=input_w,
                input_h=input_h,
                model_device=model_device,
            )
            latencies.append(time.perf_counter() - started)
            candidates.append(np.asarray(chunk, dtype=np.float32))

        cfg.seed = SEEDS[0]
        started = time.perf_counter()
        repeated0, _, _ = ev._predict_action_chunk(
            obs,
            task_description,
            model,
            processor,
            cfg,
            action_horizon=action_horizon,
            input_w=input_w,
            input_h=input_h,
            model_device=model_device,
        )
        repeat_latency = time.perf_counter() - started
    finally:
        close_libero_env(env)

    stacked = np.stack(candidates)
    repeated0 = np.asarray(repeated0, dtype=np.float32)
    pair_mad = [
        float(np.mean(np.abs(stacked[i] - stacked[j])))
        for i in range(4)
        for j in range(i + 1, 4)
    ]
    hashes = [digest(chunk) for chunk in stacked]
    repeat_error = float(np.max(np.abs(stacked[0] - repeated0)))
    finite = bool(np.isfinite(stacked).all() and np.isfinite(repeated0).all())
    gripper_values = sorted(float(x) for x in np.unique(stacked[..., -1]))
    gripper_binary = all(value in (-1.0, 0.0, 1.0) for value in gripper_values)
    passed = bool(
        stacked.shape == (4, 16, 7)
        and finite
        and len(set(hashes)) == 4
        and min(pair_mad) > 0.0
        and repeat_error <= 1e-6
        and gripper_binary
    )
    report = {
        "status": "PASS" if passed else "FAIL",
        "task_suite": "libero_mix",
        "category_value": "Background Textures",
        "task_id": 0,
        "task_description": task_description,
        "environment_seed": 10000,
        "candidate_seeds": SEEDS,
        "candidate_shape": list(stacked.shape),
        "finite": finite,
        "candidate_hashes": hashes,
        "unique_hashes": len(set(hashes)),
        "pairwise_mean_abs": pair_mad,
        "pairwise_mean_abs_min": float(min(pair_mad)),
        "pairwise_mean_abs_median": float(np.median(pair_mad)),
        "pairwise_mean_abs_mean": float(np.mean(pair_mad)),
        "gripper_values": gripper_values,
        "gripper_binary": gripper_binary,
        "candidate_latency_seconds": latencies,
        "repeat_candidate0_latency_seconds": repeat_latency,
        "candidate0_repeat_max_abs_error": repeat_error,
        "no_candidate_committed": True,
    }
    np.savez_compressed(RUN / "candidates.npz", candidates=stacked, repeated_candidate0=repeated0)
    (RUN / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
