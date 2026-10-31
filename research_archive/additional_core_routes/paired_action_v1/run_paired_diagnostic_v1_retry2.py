"""Fixed-16 paired native-action intervention diagnostic."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / "paired_action_v1"
ARCHIVE_ROOTS = (
    ROOT / "runs/qgf_gradient_training288_v1_shard0",
    ROOT / "runs/qgf_gradient_remaining257_v2_shard0",
    ROOT / "runs/qgf_gradient_remaining257_v2_shard1",
    ROOT / "runs/qgf_gradient_remaining257_v2_shard2",
    ROOT / "runs/qgf_gradient_remaining257_v2_shard3",
    ROOT / "runs/qgf_gradient_resume_v2_one",
)
SEEDS = (10000, 11000, 12000, 13000)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True))


def find_archive(episode_id):
    matches = [root / episode_id for root in ARCHIVE_ROOTS if (root / episode_id).is_dir()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one archive for {episode_id}, found {matches}")
    return matches[0]


def seed_all(seed):
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def branch_order(group):
    return sorted(range(4), key=lambda index: hashlib.sha256(
        f"paired-branch-v1|{group}|{index}".encode()).hexdigest())


def image_hash(obs):
    return hashlib.sha256(obs["agentview_image"].tobytes()
                          + obs["robot0_eye_in_hand_image"].tobytes()).hexdigest()


def image_frame(obs):
    from experiments.libero.libero_utils import get_libero_image
    images = get_libero_image(obs)
    return np.concatenate([images["image"], images["wrist_image"]], axis=1)


def load_prefix(archive):
    actions = []
    for index in range(10):
        with np.load(archive / f"transition_{index:04d}/transition.npz", allow_pickle=False) as data:
            actions.extend(np.asarray(data["executed_actions"], dtype=np.float32))
    result = np.stack(actions)
    if result.shape != (100, 7):
        raise RuntimeError(f"Archived prefix has shape {result.shape}")
    return result


def main():
    import imageio.v2 as imageio
    import torch
    from core import GuidanceConfig, GuidedScheduler
    from data_contract import (array_hash, capture_rng, observation_hash,
                               observation_payload, restore_rng, rng_hash, save_rng)
    from wam_runtime import file_sha, load_wam
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    args.run.mkdir(exist_ok=False)
    registration = json.loads((CODE / "REGISTRATION.json").read_text())
    contract = json.loads((CODE / "RASTER_CONTRACT_V2_REGISTRATION.json").read_text())
    remote_audit = json.loads((CODE / "raster_contract_v2_audit/REPORT.json").read_text())
    if contract["audit_status"] != "RASTER_CONTRACT_V2_ADMISSION_PASS":
        raise RuntimeError("Raster Contract V2 registration is not admitted")
    if remote_audit["status"] != "RASTER_CONTRACT_V2_ADMISSION_PASS":
        raise RuntimeError("Remote raster audit is not admitted")
    if len(registration["entries"]) != 16:
        raise RuntimeError("Fixed population is not 16 entries")

    cfg, model, processor = load_wam(args.run)
    from experiments.libero.eval_libero_single import _predict_action_chunk
    from experiments.libero.libero_utils import (LIBERO_ENV_RESOLUTION,
                                                  get_libero_dummy_action,
                                                  get_libero_env)
    from libero.libero import benchmark
    scheduler = model.infer_action_scheduler
    suite = benchmark.get_benchmark_dict()["libero_10"]()

    def direct_raster_hash(env):
        base = env.env if hasattr(env, "env") else env
        sim = base.sim
        first = sim.render(width=256, height=256, camera_name="agentview", mode="offscreen")
        second = sim.render(width=256, height=256,
                            camera_name="robot0_eye_in_hand", mode="offscreen")
        return hashlib.sha256(first.tobytes() + second.tobytes()).hexdigest()

    def predict(obs, description, cache, seed):
        wrapper = GuidedScheduler(scheduler, GuidanceConfig(weight=0, projected=False))
        model.infer_action_scheduler = wrapper
        cfg.seed = seed
        torch.cuda.synchronize()
        started = time.perf_counter()
        try:
            action, *_ = _predict_action_chunk(
                obs, description, model, processor, cfg, action_horizon=32,
                input_h=224, input_w=448, model_device="cuda",
                profile_action_chunk_time=True, prompt_cache=cache)
            torch.cuda.synchronize()
            native = np.asarray(action, dtype=np.float32).copy()
            if native.shape != (32, 7) or not np.isfinite(native).all():
                raise RuntimeError("Invalid native candidate")
            if not np.isin(native[..., -1], [-1, 0, 1]).all():
                raise RuntimeError("Invalid native gripper")
            return native, time.perf_counter() - started
        finally:
            model.infer_action_scheduler = scheduler

    def initialize(entry, archive):
        for key, digest in (("bddl_path", "bddl_sha256"),
                            ("initial_state_path", "initial_file_sha256")):
            if file_sha(entry[key]) != entry[digest]:
                raise RuntimeError("Frozen scene asset changed")
        task = suite.get_task(entry["task_id"])
        if task.name != entry["task_name"]:
            raise RuntimeError("Task catalogue changed")
        states = np.asarray(torch.load(entry["initial_state_path"], map_location="cpu",
                                       weights_only=False))
        if "_add_" in Path(entry["initial_state_path"]).name or "_level" in Path(entry["initial_state_path"]).name:
            states = states.reshape(1, -1)
        initial = np.asarray(states[entry["initial_state_index"]], dtype="<f8")
        if hashlib.sha256(initial.tobytes()).hexdigest() != entry["state_sha256"]:
            raise RuntimeError("Frozen initial state changed")
        seed_all(entry["environment_seed"])
        env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry["environment_seed"])
        env.reset()
        obs = env.set_init_state(initial)
        with np.load(archive / "dummy_wait.npz", allow_pickle=False) as dummy:
            for index in range(30):
                obs, reward, done, _ = env.step(get_libero_dummy_action())
                if (reward != dummy["rewards"][index] or done or env.check_success()
                        or not np.array_equal(np.asarray(env.get_sim_state()),
                                              dummy["sim_states"][index + 1])):
                    raise RuntimeError(f"Dummy replay differs at {index}")
        prefix = load_prefix(archive)
        for index, action in enumerate(prefix):
            transition, offset = divmod(index, 10)
            with np.load(archive / f"transition_{transition:04d}/transition.npz",
                         allow_pickle=False) as saved:
                obs, reward, done, _ = env.step(action.copy())
                if (reward != saved["rewards"][offset]
                        or done != saved["step_environment_done"][offset]
                        or bool(env.check_success()) != saved["step_success"][offset]
                        or not np.array_equal(np.asarray(env.get_sim_state()),
                                              saved["sim_states"][offset + 1])):
                    raise RuntimeError(f"Prefix replay differs at {index}")
        return env, obs, description, prefix

    results = []
    try:
        for entry_index, entry in enumerate(registration["entries"]):
            group_dir = args.run / entry["episode_id"]
            group_dir.mkdir()
            write_json(group_dir / "config.json", entry)
            archive = find_archive(entry["episode_id"])
            try:
                env, obs, description, prefix = initialize(entry, archive)
                cache = {}
                boundary_obs_hash = observation_hash(observation_payload(obs))
                boundary_state = np.asarray(env.get_sim_state()).copy()
                boundary_direct_hash = direct_raster_hash(env)
                before_rng = capture_rng()
                save_rng(group_dir / "rng_bank_before.npz", before_rng)
                bank, latencies, post_rngs = [], [], []
                for seed in SEEDS:
                    restore_rng(before_rng)
                    candidate, latency = predict(obs, description, cache, seed)
                    bank.append(candidate)
                    latencies.append(latency)
                    post_rngs.append(capture_rng())
                    save_rng(group_dir / f"rng_candidate_{len(post_rngs) - 1}_post.npz",
                             post_rngs[-1])
                bank = np.stack(bank)
                if len({array_hash(candidate) for candidate in bank}) != 4:
                    raise RuntimeError("N4 bank lacks four unique candidates")
                restore_rng(before_rng)
                repeat0, _ = predict(obs, description, cache, SEEDS[0])
                replay_error = float(np.max(np.abs(repeat0 - bank[0])))
                if replay_error > 1e-6:
                    raise RuntimeError("Candidate0 replay failed")
                env.close()
                np.savez_compressed(group_dir / "bank.npz", candidates_native=bank,
                                    seeds=np.asarray(SEEDS), latencies=np.asarray(latencies),
                                    boundary_state=boundary_state,
                                    boundary_observation_hash=np.asarray(boundary_obs_hash),
                                    boundary_direct_raster_hash=np.asarray(boundary_direct_hash),
                                    candidate0_replay_error=np.asarray(replay_error))
                order = branch_order(entry["physical_input_group"])
                write_json(group_dir / "branch_order.json", {"order": order})
                branch_results = []
                for candidate_index in order:
                    env, obs, branch_description, branch_prefix = initialize(entry, archive)
                    if not np.array_equal(branch_prefix, prefix):
                        raise RuntimeError("Branch prefix action schedule changed")
                    if observation_hash(observation_payload(obs)) != boundary_obs_hash:
                        raise RuntimeError("Branch policy observation differs at boundary")
                    if not np.array_equal(np.asarray(env.get_sim_state()), boundary_state):
                        raise RuntimeError("Branch simulator state differs at boundary")
                    branch_direct_hash = direct_raster_hash(env)
                    restore_rng(post_rngs[0])
                    branch_dir = group_dir / f"candidate_{candidate_index}"
                    branch_dir.mkdir()
                    writer = imageio.get_writer(branch_dir / "rollout.mp4", fps=24)
                    actions, rewards, dones, successes, states, obs_hashes = [], [], [], [], [], []
                    continuation_rng = []
                    replans = 0
                    branch_cache = {}
                    try:
                        chunk = bank[candidate_index]
                        while len(actions) < 100:
                            if replans > 0:
                                pre = capture_rng()
                                before_hash = rng_hash(pre)
                                chunk, _ = predict(obs, branch_description, branch_cache, SEEDS[0])
                                continuation_rng.append({"replan": replans,
                                                         "before": before_hash,
                                                         "after": rng_hash(capture_rng())})
                            for action in chunk[:min(10, 100 - len(actions))]:
                                obs, reward, done, _ = env.step(action.copy())
                                success = bool(env.check_success())
                                actions.append(action.copy())
                                rewards.append(float(reward))
                                dones.append(bool(done))
                                successes.append(success)
                                states.append(np.asarray(env.get_sim_state()).copy())
                                obs_hashes.append(image_hash(obs))
                                writer.append_data(image_frame(obs))
                                if done or success:
                                    break
                            replans += 1
                            if dones[-1] or successes[-1]:
                                break
                    finally:
                        writer.close()
                        env.close()
                    np.savez_compressed(branch_dir / "trajectory.npz",
                                        actions=np.stack(actions), rewards=np.asarray(rewards),
                                        done=np.asarray(dones), success=np.asarray(successes),
                                        sim_states=np.stack(states),
                                        policy_observation_hashes=np.asarray(obs_hashes))
                    result = {
                        "candidate_index": candidate_index,
                        "steps": len(actions),
                        "return": float(sum(rewards)),
                        "success": bool(successes[-1]),
                        "environment_done": bool(dones[-1]),
                        "boundary_direct_raster_hash": branch_direct_hash,
                        "bank_boundary_direct_raster_hash": boundary_direct_hash,
                        "direct_raster_boundary_equal": branch_direct_hash == boundary_direct_hash,
                        "continuation_rng": continuation_rng,
                        "trajectory_sha256": file_sha(branch_dir / "trajectory.npz"),
                        "video_sha256": file_sha(branch_dir / "rollout.mp4"),
                    }
                    write_json(branch_dir / "result.json", result)
                    branch_results.append(result)
                group_result = {
                    "status": "PAIRED_GROUP_COMPLETE",
                    "episode_id": entry["episode_id"],
                    "family": entry["family"],
                    "physical_input_group": entry["physical_input_group"],
                    "branch_order": order,
                    "branches": branch_results,
                    "differing_binary_outcome": len({row["success"] for row in branch_results}) > 1,
                }
                write_json(group_dir / "RESULT.json", group_result)
                (group_dir / "GROUP_COMPLETE").touch()
                results.append(group_result)
            except BaseException:
                (group_dir / "FAILED.txt").write_text(traceback.format_exc())
                results.append({"status": "GROUP_UNAVAILABLE", "episode_id": entry["episode_id"],
                                "family": entry["family"], "error": traceback.format_exc()})
            write_json(args.run / "progress.json", {"processed": entry_index + 1, "results": results})
            print(entry["episode_id"], results[-1]["status"], flush=True)
        complete = [row for row in results if row["status"] == "PAIRED_GROUP_COMPLETE"]
        differing = [row for row in complete if row["differing_binary_outcome"]]
        differing_families = sorted({row["family"] for row in differing})
        admitted = len(complete) >= 12 and len(differing) >= 4 and len(differing_families) >= 2
        report = {
            "status": "PAIRED_SIGNAL_GATE_PASS" if admitted else "NO_IDENTIFIABLE_SIGNAL",
            "complete_groups": len(complete),
            "unavailable_groups": 16 - len(complete),
            "differing_binary_groups": len(differing),
            "differing_families": differing_families,
            "threshold": {"complete_groups": 12, "differing_groups": 4, "differing_families": 2},
            "qgf_efficacy_claim": False,
            "results": results,
        }
        write_json(args.run / "REPORT.json", report)
        (args.run / report["status"]).touch()
        print(json.dumps(report, sort_keys=True), flush=True)
    finally:
        model.infer_action_scheduler = scheduler


if __name__ == "__main__":
    main()
