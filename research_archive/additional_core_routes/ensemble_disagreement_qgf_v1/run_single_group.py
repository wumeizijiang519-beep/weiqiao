"""Run the fixed entry-0 Progress-Pairwise QGF pilot."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np


NATIVE_SEEDS = (10000, 11000, 12000, 13000)
PROPRIO_KEYS = ("robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos")


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True))


def disk_sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_all(seed):
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def image_frame(obs):
    from experiments.libero.libero_utils import get_libero_image
    images = get_libero_image(obs)
    return np.concatenate([images["image"], images["wrist_image"]], axis=1)


def proprio_payload(obs):
    return {key: np.asarray(obs[key]).copy() for key in PROPRIO_KEYS}


def same_payload(left, right):
    return set(left) == set(right) and all(np.array_equal(left[key], right[key]) for key in left)


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
    if (result.shape != (entry["boundary_model_step"], 7)
            or hashlib.sha256(result.tobytes()).hexdigest() != entry["prefix_actions_sha256"]):
        raise RuntimeError(f"Archived prefix changed: {result.shape}")
    return result


def main():
    import imageio.v2 as imageio
    import torch
    from candidate_bank import build_bank
    from core import GuidanceConfig, GuidedScheduler
    from data_contract import (capture_rng, observation_hash, observation_payload,
                               restore_rng, save_rng)
    from progress_metric import capture as capture_progress
    from progress_metric import relative_progress
    from wam_runtime import file_sha, load_wam

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--support-bases", type=Path, required=True)
    args = parser.parse_args()
    args.run.mkdir(exist_ok=False)

    manifest = json.loads(args.manifest.read_text())
    authorization = json.loads(args.authorization.read_text())
    if manifest["status"] != "ENSEMBLE_DISAGREEMENT_QGF_V1_REGISTERED":
        raise RuntimeError("Unexpected frozen manifest status")
    if authorization["status"] != "ENSEMBLE_DISAGREEMENT_QGF_V1_GROUP_AUTHORIZED":
        raise RuntimeError("Pilot authorization missing")
    if disk_sha(args.manifest) != authorization["manifest_sha256"]:
        raise RuntimeError("Manifest changed after authorization")
    if disk_sha(args.support_bases) != manifest["support_bases_sha256"]:
        raise RuntimeError("Support bases changed")
    entry_index = int(authorization["entry_index"])
    if not 0 <= entry_index < 8 or len(manifest["entries"]) != 8:
        raise RuntimeError("Authorized entry index is outside frozen population")
    entry = authorization["entry"]
    if any(entry.get(key) != manifest["entries"][entry_index].get(key)
           for key in manifest["entries"][entry_index]):
        raise RuntimeError("Authorized entry no longer matches frozen manifest")
    archive = Path(entry["episode_directory"])
    if not archive.is_dir() or archive.name != entry["episode_id"]:
        raise RuntimeError("Frozen episode archive is missing")
    with np.load(args.support_bases, allow_pickle=False) as loaded:
        support_basis = np.asarray(loaded[entry["family"]], dtype=np.float32).copy()
    support = manifest["support"][entry["family"]]

    cfg, model, processor = load_wam(args.run)
    from experiments.libero.eval_libero_single import _predict_action_chunk
    from experiments.libero.libero_utils import (LIBERO_ENV_RESOLUTION,
                                                  get_libero_dummy_action,
                                                  get_libero_env)
    from libero.libero import benchmark
    scheduler = model.infer_action_scheduler
    suite = benchmark.get_benchmark_dict()["libero_10"]()

    action_key = processor.shape_meta["action"][0]["key"]
    normalizer = processor.normalizer.normalizers["action"][action_key]
    scale = np.broadcast_to(normalizer.scale.detach().cpu().float().numpy(), (7,)).copy()
    offset = np.broadcast_to(normalizer.offset.detach().cpu().float().numpy(), (7,)).copy()

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
            raw = wrapper.final_sample.numpy()[0].astype(np.float32, copy=True)
            if native.shape != (32, 7) or raw.shape != (32, 7):
                raise RuntimeError("Invalid model candidate shape")
            return native, raw, time.perf_counter() - started
        finally:
            model.infer_action_scheduler = scheduler

    def initialize():
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
                        or not np.array_equal(np.asarray(env.get_sim_state()), dummy["sim_states"][index + 1])):
                    raise RuntimeError(f"Dummy replay differs at {index}")
        prefix = load_prefix(entry, archive)
        global_index = 0
        for transition in range(entry["boundary_replan"]):
            with np.load(archive / f"transition_{transition:04d}/transition.npz", allow_pickle=False) as saved:
                actual = int(saved["actual_length"])
                for offset_index, action in enumerate(saved["executed_actions"][:actual]):
                    obs, reward, done, _ = env.step(action.copy())
                    if (reward != saved["rewards"][offset_index]
                            or done != saved["step_environment_done"][offset_index]
                            or bool(env.check_success()) != saved["step_success"][offset_index]
                            or not np.array_equal(np.asarray(env.get_sim_state()), saved["sim_states"][offset_index + 1])):
                        raise RuntimeError(f"Prefix replay differs at {global_index}")
                    global_index += 1
        if global_index != entry["boundary_model_step"]:
            raise RuntimeError("Prefix replay step count changed")
        with np.load(entry["boundary_observation_path"], allow_pickle=False) as saved_obs:
            archived = observation_payload({key: saved_obs[key] for key in saved_obs.files
                                            if key in ("agentview_image", "robot0_eye_in_hand_image", *PROPRIO_KEYS)})
        if disk_sha(entry["boundary_observation_path"]) != entry["boundary_observation_sha256"]:
            raise RuntimeError("Frozen boundary observation changed")
        current = observation_payload(obs)
        legacy_match = (set(archived) == set(current)
                        and all(np.array_equal(archived[key], current[key]) for key in archived))
        return env, obs, description, prefix, legacy_match

    group_dir = args.run / entry["episode_id"]
    group_dir.mkdir()
    write_json(group_dir / "config.json", entry)
    try:
        env, obs, description, prefix, legacy_match = initialize()
        cache = {}
        boundary_observation = observation_payload(obs)
        boundary_hash = observation_hash(boundary_observation)
        boundary_proprio = proprio_payload(obs)
        boundary_state = np.asarray(env.get_sim_state()).copy()
        boundary_progress = capture_progress(env, entry["family"])
        np.savez_compressed(group_dir / "frozen_policy_input.npz", **boundary_observation)
        before_rng = capture_rng()
        save_rng(group_dir / "rng_bank_before.npz", before_rng)
        native4, raw4, latencies, post_rngs = [], [], [], []
        for index, seed in enumerate(NATIVE_SEEDS):
            restore_rng(before_rng)
            native, raw, latency = predict(obs, description, cache, seed)
            native4.append(native)
            raw4.append(raw)
            latencies.append(latency)
            post_rngs.append(capture_rng())
            save_rng(group_dir / f"rng_native_{index}_post.npz", post_rngs[-1])
        bank = build_bank(np.stack(native4), np.stack(raw4), scale, offset,
                          support_basis, support["median_delta_norm"], support["p95_delta_norm"])
        restore_rng(before_rng)
        repeat_native, repeat_raw, _ = predict(obs, description, cache, NATIVE_SEEDS[0])
        replay_error = max(float(np.max(np.abs(repeat_native - bank["native"][0]))),
                           float(np.max(np.abs(repeat_raw - bank["raw_normalized"][0]))))
        if replay_error > 1e-6:
            raise RuntimeError("Candidate0 native/raw replay failed")
        env.close()
        np.savez_compressed(group_dir / "bank.npz",
                            candidates_native=bank["native"],
                            candidates_raw_normalized=bank["raw_normalized"],
                            candidates_executed_normalized=bank["executed_normalized"],
                            hashes=np.asarray(bank["hashes"]),
                            structured_delta_norms=np.asarray(bank["structured_delta_norms"]),
                            native_seeds=np.asarray(NATIVE_SEEDS), latencies=np.asarray(latencies),
                            scale=scale, offset=offset, boundary_state=boundary_state,
                            boundary_observation_hash=np.asarray(boundary_hash),
                            candidate0_replay_error=np.asarray(replay_error))

        order = sorted(range(8), key=lambda index: hashlib.sha256(
            f"progress-pairwise-qgf-v1|{entry['physical_input_group']}|{index}".encode()).hexdigest())
        write_json(group_dir / "branch_order.json", {"order": order})
        branch_results = []
        for candidate_index in order:
            env, obs, branch_description, branch_prefix, branch_legacy_match = initialize()
            if branch_description != description or not np.array_equal(branch_prefix, prefix):
                raise RuntimeError("Branch reconstruction contract changed")
            if not np.array_equal(np.asarray(env.get_sim_state()), boundary_state):
                raise RuntimeError("Branch simulator state differs at boundary")
            if not same_payload(proprio_payload(obs), boundary_proprio):
                raise RuntimeError("Branch proprioception differs at boundary")
            branch_observation_hash = observation_hash(observation_payload(obs))
            restore_rng(post_rngs[0])
            branch_dir = group_dir / f"candidate_{candidate_index}"
            branch_dir.mkdir()
            writer = imageio.get_writer(branch_dir / "rollout.mp4", fps=24)
            actions, rewards, dones, successes, states = [], [], [], [], []
            progress_at_16 = None
            success_at_16 = None
            try:
                for step_index, action in enumerate(bank["native"][candidate_index], start=1):
                    obs, reward, done, _ = env.step(action.copy())
                    success = bool(env.check_success())
                    actions.append(action.copy())
                    rewards.append(float(reward))
                    dones.append(bool(done))
                    successes.append(success)
                    states.append(np.asarray(env.get_sim_state()).copy())
                    writer.append_data(image_frame(obs))
                    if step_index == 16:
                        progress_at_16 = capture_progress(env, entry["family"])
                        success_at_16 = success
                    if done or success:
                        break
                final_progress = capture_progress(env, entry["family"])
                if progress_at_16 is None:
                    progress_at_16 = final_progress
                    success_at_16 = bool(successes[-1])
            finally:
                writer.close()
                env.close()
            executed = np.stack(actions)
            commit_error = float(np.max(np.abs(executed - bank["native"][candidate_index, :len(actions)])))
            if commit_error > 1e-6:
                raise RuntimeError("Executed candidate prefix differs from bank")
            np.savez_compressed(branch_dir / "trajectory.npz", actions=executed,
                                rewards=np.asarray(rewards), done=np.asarray(dones),
                                success=np.asarray(successes), sim_states=np.stack(states))
            result = {
                "candidate_index": candidate_index,
                "candidate_kind": "native" if candidate_index < 4 else "ensemble_disagreement",
                "steps": len(actions), "return": float(sum(rewards)),
                "success_at_16": bool(success_at_16), "success_at_32": bool(successes[-1]),
                "environment_done": bool(dones[-1]),
                "progress_state_at_16": progress_at_16,
                "progress_state_at_32": final_progress,
                "progress_at_16": relative_progress(boundary_progress, progress_at_16, entry["family"]),
                "progress_at_32": relative_progress(boundary_progress, final_progress, entry["family"]),
                "commit_max_error": commit_error,
                "branch_boundary_observation_hash": branch_observation_hash,
                "branch_matches_source_policy_input": branch_observation_hash == boundary_hash,
                "branch_matches_legacy_archive_policy_input": branch_legacy_match,
                "trajectory_sha256": file_sha(branch_dir / "trajectory.npz"),
                "video_sha256": file_sha(branch_dir / "rollout.mp4"),
            }
            write_json(branch_dir / "result.json", result)
            branch_results.append(result)
        report = {
            "status": "ENSEMBLE_DISAGREEMENT_GROUP_COMPLETE",
            "episode_id": entry["episode_id"], "family": entry["family"],
            "physical_input_group": entry["physical_input_group"],
            "boundary_progress_state": boundary_progress, "branch_order": order,
            "boundary_contract": "RUNTIME_ANCHORED_SINGLE_SOURCE_POLICY_INPUT_V1",
            "source_matches_legacy_archive_policy_input": legacy_match,
            "branches": branch_results, "candidate_hashes": bank["hashes"],
            "candidate0_replay_error": replay_error, "qgf_efficacy_claim": False,
        }
        write_json(args.run / "REPORT.json", report)
        (args.run / "PILOT_RETURNED").touch()
        print(json.dumps(report, sort_keys=True), flush=True)
    except BaseException:
        (args.run / "FAILED.txt").write_text(traceback.format_exc())
        raise
    finally:
        model.infer_action_scheduler = scheduler


if __name__ == "__main__":
    main()
