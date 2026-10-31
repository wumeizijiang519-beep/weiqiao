"""Fixed-16 N8 diagnostic at preregistered failure-critical boundaries."""
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
SEEDS = (10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000)
PROPRIO_KEYS = ("robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True))


def disk_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_archive(entry):
    archive = Path(entry["episode_directory"])
    if not archive.is_dir() or archive.name != entry["episode_id"]:
        raise RuntimeError("Frozen episode archive is missing")
    return archive


def seed_all(seed):
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def branch_order(group):
    return sorted(range(8), key=lambda index: hashlib.sha256(
        f"failure-critical-boundary-v1|{group}|{index}".encode()).hexdigest())


def image_hash(obs):
    return hashlib.sha256(obs["agentview_image"].tobytes()
                          + obs["robot0_eye_in_hand_image"].tobytes()).hexdigest()


def image_frame(obs):
    from experiments.libero.libero_utils import get_libero_image
    images = get_libero_image(obs)
    return np.concatenate([images["image"], images["wrist_image"]], axis=1)


def proprio_payload(obs):
    return {key: np.asarray(obs[key]).copy() for key in PROPRIO_KEYS}


def same_payload(left, right):
    return all(np.array_equal(left[key], right[key]) for key in left)


def load_prefix(entry, archive):
    actions = []
    if len(entry["transition_receipts"]) != entry["boundary_replan"]:
        raise RuntimeError("Frozen transition inventory changed")
    for index, receipt in enumerate(entry["transition_receipts"]):
        path = archive / f"transition_{index:04d}/transition.npz"
        if disk_sha(path) != receipt["sha256"] or receipt["index"] != index:
            raise RuntimeError("Frozen transition receipt changed")
        with np.load(path, allow_pickle=False) as data:
            actual = int(data["actual_length"])
            if actual != receipt["actual_length"]:
                raise RuntimeError("Frozen transition length changed")
            actions.extend(np.asarray(data["executed_actions"][:actual], dtype=np.float32))
    result = np.stack(actions) if actions else np.empty((0, 7), dtype=np.float32)
    if (result.shape != (entry["prefix_steps"], 7)
            or hashlib.sha256(result.tobytes()).hexdigest() != entry["prefix_actions_sha256"]):
        raise RuntimeError(f"Archived prefix changed: {result.shape}")
    return result


def main():
    import imageio.v2 as imageio
    import torch
    from core import GuidanceConfig, GuidedScheduler
    from data_contract import (array_hash, capture_rng, observation_hash,
                               observation_payload, restore_rng, rng_hash, save_rng)
    from wam_runtime import file_sha, load_wam
    from boundary_anchored_metrics import goal_fraction
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--entry-start", type=int, default=0)
    parser.add_argument("--entry-stop", type=int, default=16)
    args = parser.parse_args()
    args.run.mkdir(exist_ok=False)
    registration = json.loads(args.manifest.read_text())
    if registration["status"] != "FAILURE_CRITICAL_BOUNDARY_V1_REGISTERED_AND_AUTHORIZED":
        raise RuntimeError("Failure-critical execution is not authorized")
    if len(registration["entries"]) != 16:
        raise RuntimeError("Fixed population is not 16 entries")
    if not (0 <= args.entry_start < args.entry_stop <= 16):
        raise RuntimeError("Invalid frozen entry slice")
    selected_entries = registration["entries"][args.entry_start:args.entry_stop]

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
        prefix = load_prefix(entry, archive)
        global_index = 0
        for transition in range(entry["boundary_replan"]):
            with np.load(archive / f"transition_{transition:04d}/transition.npz", allow_pickle=False) as saved:
                actual = int(saved["actual_length"])
                for offset, action in enumerate(saved["executed_actions"][:actual]):
                    obs, reward, done, _ = env.step(action.copy())
                    if (reward != saved["rewards"][offset]
                            or done != saved["step_environment_done"][offset]
                            or bool(env.check_success()) != saved["step_success"][offset]
                            or not np.array_equal(np.asarray(env.get_sim_state()),
                                                  saved["sim_states"][offset + 1])):
                        raise RuntimeError(f"Prefix replay differs at {global_index}")
                    global_index += 1
        if global_index != entry["prefix_steps"]:
            raise RuntimeError("Prefix replay step count changed")
        archived_observation = observation_payload({
            key: value for key, value in np.load(entry["boundary_observation_path"], allow_pickle=False).items()
            if key in ("agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
                       "robot0_eef_quat", "robot0_gripper_qpos")})
        if disk_sha(entry["boundary_observation_path"]) != entry["boundary_observation_sha256"]:
            raise RuntimeError("Frozen boundary observation changed")
        current_observation = observation_payload(obs)
        if (set(archived_observation) != set(current_observation)
                or not all(np.array_equal(archived_observation[key], current_observation[key])
                           for key in archived_observation)):
            raise RuntimeError("Reconstructed boundary policy input differs from archive")
        return env, obs, description, prefix

    results = []
    try:
        for entry_index, entry in enumerate(selected_entries, start=args.entry_start):
            group_dir = args.run / entry["episode_id"]
            group_dir.mkdir()
            write_json(group_dir / "config.json", entry)
            archive = find_archive(entry)
            try:
                env, obs, description, prefix = initialize(entry, archive)
                cache = {}
                frozen_policy_input = observation_payload(obs)
                boundary_obs_hash = observation_hash(frozen_policy_input)
                boundary_proprio = proprio_payload(obs)
                boundary_state = np.asarray(env.get_sim_state()).copy()
                boundary_direct_hash = direct_raster_hash(env)
                np.savez_compressed(group_dir / "frozen_policy_input.npz",
                                    **frozen_policy_input)
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
                if bank.shape != (8, 32, 7):
                    raise RuntimeError(f"Invalid N8 bank shape {bank.shape}")
                if len({array_hash(candidate) for candidate in bank}) != 8:
                    raise RuntimeError("N8 bank lacks eight unique candidates")
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
                    if not np.array_equal(np.asarray(env.get_sim_state()), boundary_state):
                        raise RuntimeError("Branch simulator state differs at boundary")
                    if not same_payload(proprio_payload(obs), boundary_proprio):
                        raise RuntimeError("Branch proprioception differs at boundary")
                    branch_obs_hash = observation_hash(observation_payload(obs))
                    branch_direct_hash = direct_raster_hash(env)
                    restore_rng(post_rngs[0])
                    branch_dir = group_dir / f"candidate_{candidate_index}"
                    branch_dir.mkdir()
                    writer = imageio.get_writer(branch_dir / "rollout.mp4", fps=24)
                    actions, rewards, dones, successes, states, obs_hashes = [], [], [], [], [], []
                    start_goal_fraction = goal_fraction(env)
                    goal_fraction_at_16 = None
                    success_at_16 = None
                    try:
                        chunk = bank[candidate_index]
                        for step_index, action in enumerate(chunk[:32], start=1):
                            obs, reward, done, _ = env.step(action.copy())
                            success = bool(env.check_success())
                            actions.append(action.copy())
                            rewards.append(float(reward))
                            dones.append(bool(done))
                            successes.append(success)
                            states.append(np.asarray(env.get_sim_state()).copy())
                            obs_hashes.append(image_hash(obs))
                            writer.append_data(image_frame(obs))
                            if step_index == 16:
                                goal_fraction_at_16 = goal_fraction(env)
                                success_at_16 = success
                            if done or success:
                                break
                        final_goal_fraction = goal_fraction(env)
                        if goal_fraction_at_16 is None:
                            goal_fraction_at_16 = final_goal_fraction
                            success_at_16 = bool(successes[-1])
                    finally:
                        writer.close()
                        env.close()
                    np.savez_compressed(branch_dir / "trajectory.npz",
                                        actions=np.stack(actions), rewards=np.asarray(rewards),
                                        done=np.asarray(dones), success=np.asarray(successes),
                                        sim_states=np.stack(states),
                                        policy_observation_hashes=np.asarray(obs_hashes))
                    executed = np.stack(actions)
                    commit_error = float(np.max(np.abs(executed - bank[candidate_index, :len(actions)])))
                    if commit_error > 1e-6:
                        raise RuntimeError("Executed candidate prefix differs from candidate bank")
                    result = {
                        "candidate_index": candidate_index,
                        "steps": len(actions),
                        "return": float(sum(rewards)),
                        "success": bool(successes[-1]),
                        "environment_done": bool(dones[-1]),
                        "boundary_direct_raster_hash": branch_direct_hash,
                        "bank_boundary_direct_raster_hash": boundary_direct_hash,
                        "direct_raster_boundary_equal": branch_direct_hash == boundary_direct_hash,
                        "branch_policy_observation_hash": branch_obs_hash,
                        "bank_policy_observation_hash": boundary_obs_hash,
                        "policy_observation_equal_audit_only": branch_obs_hash == boundary_obs_hash,
                        "start_goal_fraction": start_goal_fraction,
                        "goal_fraction_at_16": goal_fraction_at_16,
                        "success_at_16": success_at_16,
                        "final_goal_fraction": final_goal_fraction,
                        "commit_max_error": commit_error,
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
                    "successes": [row["success"] for row in branch_results],
                    "successes_at_16": [row["success_at_16"] for row in branch_results],
                    "final_goal_fractions": [row["final_goal_fraction"] for row in branch_results],
                    "goal_fractions_at_16": [row["goal_fraction_at_16"] for row in branch_results],
                    "differing_binary_outcome": len({row["success"] for row in branch_results}) > 1,
                    "differing_binary_outcome_at_16": len({row["success_at_16"] for row in branch_results}) > 1,
                }
                write_json(group_dir / "RESULT.json", group_result)
                (group_dir / "GROUP_COMPLETE").touch()
                results.append(group_result)
            except BaseException:
                (group_dir / "FAILED.txt").write_text(traceback.format_exc())
                results.append({"status": "GROUP_UNAVAILABLE", "episode_id": entry["episode_id"],
                                "family": entry["family"], "error": traceback.format_exc()})
            write_json(args.run / "progress.json", {
                "entry_start": args.entry_start, "entry_stop": args.entry_stop,
                "processed": len(results), "results": results})
            print(entry["episode_id"], results[-1]["status"], flush=True)
        qualification = {
            "complete_groups": sum(row["status"] == "PAIRED_GROUP_COMPLETE" for row in results),
            "status": "PARTIAL_EXECUTION_COMPLETE",
        }
        report = {
            **qualification,
            "entry_start": args.entry_start,
            "entry_stop": args.entry_stop,
            "unavailable_groups": len(results) - qualification["complete_groups"],
            "threshold": {"complete_groups": 12, "binary_groups": 4,
                          "binary_families": 2, "dense_bootstrap_families": 2,
                          "bootstrap_seed": 202641401, "bootstrap_draws": 10000},
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
