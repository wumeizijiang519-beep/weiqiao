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
from experiments.libero.libero_utils import (
    close_libero_env,
    get_libero_dummy_action,
    get_libero_env,
    get_libero_image,
    save_rollout_video,
)


RUN = Path(os.environ["KAIROS_INTERVENTION_RUN"])
CONFIG_DIR = os.environ["KAIROS_LIBERO_CONFIG_DIR"]
STATS = os.environ["DATASET_STATS_PATH"]
ENDPOINT = os.environ["MODEL_ENDPOINT"]
SHARD = int(os.environ["KAIROS_INTERVENTION_SHARD"])
CANDIDATE_SEEDS = [10000, 11000, 12000, 13000]
SPECS = {
    0: [(202633101, 1, 202633501), (202633102, 2, 202633502)],
    1: [(202633201, 3, 202633601), (202633202, 4, 202633602)],
}


def digest(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array, dtype=np.float32).tobytes()).hexdigest()


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    with initialize_config_dir(version_base="1.3", config_dir=CONFIG_DIR):
        cfg = compose(
            config_name="sim_libero.yaml",
            overrides=[
                "task=libero_uncond_2cam224_1e-4",
                "model=external_model_adapter",
                f"model.endpoint={ENDPOINT}",
                "ckpt=/nothing/to/load",
                "seed=10000",
                "gpu_id=0",
                "EVALUATION.task_suite_name=libero_mix",
                "EVALUATION.task_id=0",
                "EVALUATION.category_value=Background Textures",
                f"EVALUATION.dataset_stats_path={STATS}",
                f"EVALUATION.output_dir={RUN / 'output'}",
                "EVALUATION.num_steps_wait=30",
                "EVALUATION.replan_steps=10",
                "EVALUATION.binarize_gripper=true",
                "EVALUATION.num_inference_steps=20",
            ],
        )

    model_device = ev._resolve_eval_device(cfg)
    model_dtype = ev._mixed_precision_to_model_dtype(cfg.get("mixed_precision", "bf16"))
    model = instantiate(cfg.model, model_dtype=model_dtype, device=model_device).to(model_device).eval()
    processor = instantiate(cfg.data.train.processor).eval()
    processor.set_normalizer_from_stats(load_dataset_stats_from_json(STATS))
    action_horizon = int(cfg.data.train.num_frames) - 1
    input_h, input_w = (int(value) for value in cfg.data.train.video_size)

    suite = benchmark.get_benchmark_dict()["libero_mix"](category_value="Background Textures")
    task = suite.get_task(0)
    initial_states = list(suite.get_task_init_states(0))
    summaries = []

    for episode_index, (env_seed, init_index, selection_seed) in enumerate(SPECS[SHARD]):
        episode_dir = RUN / f"episode_{episode_index}"
        episode_dir.mkdir(parents=True, exist_ok=True)
        rng = np.random.default_rng(selection_seed)
        env, task_description = get_libero_env(task, ev.LIBERO_ENV_RESOLUTION, env_seed)
        replay = []
        transitions = []
        try:
            env.reset()
            obs = env.set_init_state(initial_states[init_index])
            done = False
            for _ in range(30):
                obs, _, done, _ = env.step(get_libero_dummy_action())

            env_step = 30
            replan_index = 0
            while env_step < 550 and not done:
                candidates = []
                latencies = []
                image = get_libero_image(obs)
                if isinstance(image, dict):
                    observation_arrays = {
                        f"observation_{key}": np.asarray(value, dtype=np.uint8)
                        for key, value in image.items()
                    }
                else:
                    observation_arrays = {
                        "observation_image": np.asarray(image, dtype=np.uint8)
                    }
                for seed in CANDIDATE_SEEDS:
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
                stacked = np.stack(candidates)
                hashes = [digest(chunk) for chunk in stacked]
                if stacked.shape != (4, 32, 7) or not np.isfinite(stacked).all() or len(set(hashes)) != 4:
                    raise RuntimeError("candidate contract failed")

                selected = int(rng.integers(0, 4))
                rewards = []
                executed = []
                for action in stacked[selected, :10]:
                    executed.append(np.asarray(action, dtype=np.float32))
                    obs, reward, done, _ = env.step(action.tolist())
                    rewards.append(float(reward))
                    replay.append(get_libero_image(obs))
                    env_step += 1
                    if done:
                        break
                executed_array = np.stack(executed)
                commit_error = float(np.max(np.abs(executed_array[0] - stacked[selected, 0])))
                if commit_error > 1e-6:
                    raise RuntimeError(f"selected/committed action mismatch: {commit_error}")
                np.savez_compressed(
                    episode_dir / f"replan_{replan_index:04d}.npz",
                    candidates=stacked,
                    selected_index=np.int64(selected),
                    executed_actions=executed_array,
                    rewards=np.asarray(rewards, dtype=np.float32),
                    **observation_arrays,
                )
                transitions.append(
                    {
                        "replan_index": replan_index,
                        "env_step_start": env_step - len(rewards),
                        "candidate_hashes": hashes,
                        "selected_index": selected,
                        "executed_steps": len(rewards),
                        "finite_horizon_return": float(sum(rewards)),
                        "commit_max_abs_error": commit_error,
                        "candidate_latency_seconds": latencies,
                    }
                )
                replan_index += 1
        finally:
            close_libero_env(env)

        save_rollout_video(
            episode_dir,
            replay,
            f"shard{SHARD}_episode{episode_index}",
            success=bool(done),
            task_description=task_description,
        )
        summary = {
            "shard": SHARD,
            "episode_index": episode_index,
            "environment_seed": env_seed,
            "initial_state_index": init_index,
            "selection_seed": selection_seed,
            "success": bool(done),
            "environment_steps": env_step,
            "replans": len(transitions),
            "transitions": transitions,
        }
        (episode_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        summaries.append(summary)

    report = {
        "status": "COMPLETE",
        "shard": SHARD,
        "episodes": len(summaries),
        "successes": sum(int(item["success"]) for item in summaries),
        "failures": sum(int(not item["success"]) for item in summaries),
        "summaries": summaries,
    }
    (RUN / "shard_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
