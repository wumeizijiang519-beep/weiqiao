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


PLANS = {
    "task0": {"task_id": 0, "shards": {0: [
        {"init_idx": 1, "env_seed": 202630101, "selection_seed": 202630501},
        {"init_idx": 2, "env_seed": 202630102, "selection_seed": 202630502},
    ], 1: [
        {"init_idx": 3, "env_seed": 202630201, "selection_seed": 202630601},
        {"init_idx": 4, "env_seed": 202630202, "selection_seed": 202630602},
    ]}},
    "task1": {"task_id": 1, "shards": {0: [
        {"init_idx": 5, "env_seed": 202631101, "selection_seed": 202631501},
        {"init_idx": 6, "env_seed": 202631102, "selection_seed": 202631502},
    ], 1: [
        {"init_idx": 7, "env_seed": 202631201, "selection_seed": 202631601},
        {"init_idx": 8, "env_seed": 202631202, "selection_seed": 202631602},
    ]}},
}
CANDIDATE_SEEDS = [10000, 11000, 12000, 13000]


def sha(chunk):
    return hashlib.sha256(np.asarray(chunk, dtype=np.float32).tobytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--shard", type=int, choices=[0, 1], required=True)
    parser.add_argument("--plan", choices=sorted(PLANS), default="task0")
    args = parser.parse_args()
    plan = PLANS[args.plan]
    task_id = int(plan["task_id"])

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / "videos").mkdir()
    imagewam = root / "backbones" / "ImageWAM"
    checkpoint = root / "checkpoints_first_tier" / "imagewam" / "libero_plus" / "model.pt"
    stats_path = checkpoint.parent / "dataset_stats.json"
    flux2 = imagewam / "third_party" / "flux2"
    flux2_model = root / "checkpoints_first_tier" / "imagewam" / "flux2" / "FLUX.2-klein-base-4B" / "flux-2-klein-base-4b.safetensors"
    ae_model = root / "checkpoints_first_tier" / "imagewam" / "flux2" / "FLUX.2-public-vae-bfl-layout" / "ae.safetensors"
    qwen_model = root / "checkpoints_first_tier" / "imagewam" / "flux2" / "Qwen3-4B"
    sys.path.insert(0, str(imagewam / "experiments" / "libero"))

    overrides = [
        "task=libero_flux2_klein_4b_base_imagewam",
        f"ckpt={checkpoint}", "gpu_id=0", "seed=10000",
        f"EVALUATION.dataset_stats_path={stats_path}",
        "EVALUATION.task_suite_name=libero_10", f"EVALUATION.task_id={task_id}",
        "EVALUATION.num_trials=1", "EVALUATION.action_horizon=16",
        "EVALUATION.replan_steps=12", "EVALUATION.num_steps_wait=30",
        f"model.flux2_src_path={flux2}", f"model.flux2_model_path={flux2_model}",
        f"model.ae_model_path={ae_model}", "model.variant=klein-base-4b",
        f"model.qwen3_model_spec={qwen_model}", "model.qwen_context_len=128",
        "model.load_text_encoder=true", "model.pack_proprio_after_text=true",
        "model.proprio_dim=8", "model.flux2_lora_config.enabled=false",
        "data.train.qwen_text_cache_format=qwen3_flux2",
    ]
    with initialize_config_dir(version_base="1.3", config_dir=str(imagewam / "configs")):
        cfg = compose(config_name="sim_libero_omnigen2", overrides=overrides)

    from experiments.libero import eval_libero_single as ev
    from experiments.libero.libero_utils import (
        LIBERO_ENV_RESOLUTION, get_libero_dummy_action, get_libero_env,
        get_libero_image, save_rollout_video,
    )
    from imagewam.datasets.lerobot.utils.normalizer import load_dataset_stats_from_json
    from libero.libero import benchmark

    model_cfg = ev._resolve_model_cfg(cfg)
    model = instantiate(model_cfg, model_dtype=torch.bfloat16, device="cuda")
    ev._load_model_checkpoint(model, str(checkpoint))
    model = model.to("cuda").eval()
    stats = load_dataset_stats_from_json(str(stats_path))
    processor = instantiate(cfg.data.train.processor).eval()
    processor.set_normalizer_from_stats(stats)

    suite = benchmark.get_benchmark_dict()["libero_10"]()
    task = suite.get_task(task_id)
    summaries = []
    for episode_index, spec in enumerate(plan["shards"][args.shard]):
        env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, spec["env_seed"])
        env.reset()
        obs = env.set_init_state(suite.get_task_init_states(task_id)[spec["init_idx"]])
        replay_images = []
        for _ in range(30):
            replay_images.append(get_libero_image(obs))
            obs, _, done, _ = env.step(get_libero_dummy_action())
            if done:
                raise RuntimeError("episode terminated during dummy wait")

        rng = np.random.default_rng(spec["selection_seed"])
        current_head, current_wrist, current_proprio = [], [], []
        next_head, next_wrist, next_proprio = [], [], []
        candidates_all, selected_all, executed_all = [], [], []
        actual_lengths, rewards_all, hashes_all, latencies_all = [], [], [], []
        commit_errors, returns = [], []
        total_steps = 0
        success = False

        while total_steps < 700 and not success:
            replan_proprio = ev._extract_sim_state(obs).copy()
            chunks, latencies = [], []
            candidate_images = None
            for candidate_seed in CANDIDATE_SEEDS:
                cfg.seed = candidate_seed
                start = time.perf_counter()
                chunk, candidate_images, _ = ev._predict_action_chunk(
                    obs, description, model, processor, cfg,
                    action_horizon=16, input_w=448, input_h=224,
                    model_device="cuda",
                )
                torch.cuda.synchronize()
                latencies.append(time.perf_counter() - start)
                chunks.append(np.asarray(chunk, dtype=np.float32))
            candidates = np.stack(chunks)
            if candidates.shape != (4, 16, 7) or not np.isfinite(candidates).all():
                raise RuntimeError(f"invalid candidates {candidates.shape}")
            hashes = [sha(x) for x in candidates]
            if len(set(hashes)) != 4:
                raise RuntimeError("candidate hashes are not all distinct")
            if not np.all(np.isin(candidates[..., -1], [-1.0, 0.0, 1.0])):
                raise RuntimeError("gripper contract failed")

            selected = int(rng.integers(0, 4))
            planned = candidates[selected, : min(12, 700 - total_steps)].copy()
            executed, step_rewards = [], []
            for action in planned:
                committed = np.asarray(action, dtype=np.float32).copy()
                obs, reward, done, _ = env.step(committed)
                executed.append(committed)
                step_rewards.append(float(reward))
                replay_images.append(get_libero_image(obs))
                total_steps += 1
                if done or total_steps >= 700:
                    success = bool(done)
                    break
            executed = np.stack(executed)
            commit_error = float(np.max(np.abs(executed - planned[: len(executed)])))
            if commit_error > 1e-6:
                raise RuntimeError(f"commit error {commit_error}")

            nxt = get_libero_image(obs)
            current_head.append(np.asarray(candidate_images["image"], dtype=np.uint8))
            current_wrist.append(np.asarray(candidate_images["wrist_image"], dtype=np.uint8))
            current_proprio.append(replan_proprio)
            next_head.append(np.asarray(nxt["image"], dtype=np.uint8))
            next_wrist.append(np.asarray(nxt["wrist_image"], dtype=np.uint8))
            next_proprio.append(ev._extract_sim_state(obs))
            candidates_all.append(candidates)
            selected_all.append(selected)
            executed_all.append(executed)
            actual_lengths.append(len(executed))
            rewards_all.append(np.asarray(step_rewards, dtype=np.float32))
            hashes_all.append(hashes)
            latencies_all.append(latencies)
            commit_errors.append(commit_error)
            returns.append(float(np.sum(step_rewards)))

        episode_id = f"task{task_id}_shard{args.shard}_episode{episode_index}_seed{spec['env_seed']}"
        max_exec = 12
        executed_padded = np.zeros((len(executed_all), max_exec, 7), dtype=np.float32)
        rewards_padded = np.zeros((len(rewards_all), max_exec), dtype=np.float32)
        for i, (acts, rewards) in enumerate(zip(executed_all, rewards_all)):
            executed_padded[i, : len(acts)] = acts
            rewards_padded[i, : len(rewards)] = rewards
        npz_path = output / f"{episode_id}.npz"
        np.savez_compressed(
            npz_path,
            current_head=np.stack(current_head), current_wrist=np.stack(current_wrist),
            current_proprio=np.stack(current_proprio),
            candidates=np.stack(candidates_all), selected_index=np.asarray(selected_all),
            executed=executed_padded, actual_length=np.asarray(actual_lengths),
            rewards=rewards_padded, finite_horizon_return=np.asarray(returns),
            next_head=np.stack(next_head), next_wrist=np.stack(next_wrist),
            next_proprio=np.stack(next_proprio),
            candidate_hashes=np.asarray(hashes_all),
            candidate_seeds=np.asarray(CANDIDATE_SEEDS),
            environment_seed=np.asarray(spec["env_seed"]),
            selection_seed=np.asarray(spec["selection_seed"]),
            initial_state_index=np.asarray(spec["init_idx"]),
            success=np.asarray(success),
        )
        save_rollout_video(output / "videos", replay_images, episode_index, success, description)
        summaries.append({
            **spec, "episode_id": episode_id, "success": success,
            "steps": total_steps, "replans": len(selected_all),
            "max_commit_error": max(commit_errors),
            "mean_candidate_latency_seconds": float(np.mean(latencies_all)),
            "npz": str(npz_path), "npz_sha256": hashlib.sha256(npz_path.read_bytes()).hexdigest(),
        })
        env.close()

    report = {
        "status": "COMPLETE", "plan": args.plan, "task_id": task_id, "shard": args.shard,
        "candidate_seeds": CANDIDATE_SEEDS, "episodes": summaries,
        "successes": sum(int(x["success"]) for x in summaries),
        "failures": sum(int(not x["success"]) for x in summaries),
        "cuda_peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "SHARD_COMPLETE").touch()


if __name__ == "__main__":
    main()

