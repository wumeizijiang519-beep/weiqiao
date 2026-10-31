"""Execute one frozen held-out scene/arm task with equal shadow-Q compute."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time

import imageio.v2 as imageio
import numpy as np
import torch

from export_features import Extractor
from simplewam_visual_rl.deployment import FrozenVisualQ, QGFConfig
from simplewam_visual_rl.online_contract import select_online_arm
from simplewam_visual_rl.scheduler import EqualComputeVisualQScheduler
from data_contract import array_hash, capture_rng, observation_payload, save_rng
from wam_runtime import file_sha, load_wam


SEEDS = (10000, 11000, 12000, 13000)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)


def proprio(obs):
    return np.concatenate((obs["robot0_eef_pos"], obs["robot0_eef_quat"], obs["robot0_gripper_qpos"])).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--task-index", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    registration_path = base / "formal_online_registration_v1/REGISTRATION.json"
    registration = json.loads(registration_path.read_text())
    task_receipt = registration["tasks"][args.task_index]
    if task_receipt["task_index"] != args.task_index:
        raise RuntimeError("online task index changed")
    cohort = json.loads(Path(registration["cohort_manifest"]).read_text())
    entry = cohort["partitions"]["formal"][task_receipt["formal_manifest_index"]]
    deployment = json.loads(Path(registration["deployment_registration"]).read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(args.output / "task.json", task_receipt)
    write_json(args.output / "scene.json", entry)

    from experiments.libero.eval_libero_single import _predict_action_chunk
    from experiments.libero.libero_utils import LIBERO_ENV_RESOLUTION, get_libero_dummy_action, get_libero_env, get_libero_image
    from libero.libero import benchmark

    for key, digest_key in (("initial_state_path", "initial_file_sha256"), ("bddl_path", "bddl_sha256")):
        if file_sha(entry[key]) != entry[digest_key]:
            raise RuntimeError("held-out scene asset mismatch")
    states = np.asarray(torch.load(entry["initial_state_path"], map_location="cpu", weights_only=False))
    if "_add_" in Path(entry["initial_state_path"]).name or "_level" in Path(entry["initial_state_path"]).name:
        states = states.reshape(1, -1)
    initial = np.asarray(states[entry["initial_state_index"]], dtype="<f8")
    if hashlib.sha256(initial.tobytes()).hexdigest() != entry["state_sha256"]:
        raise RuntimeError("held-out initial state mismatch")
    seed_all(entry["environment_seed"])
    suite = benchmark.get_benchmark_dict()["libero_10"]()
    lib_task = suite.get_task(entry["task_id"])
    if lib_task.name != entry["task_name"]:
        raise RuntimeError("held-out task catalogue changed")
    env, description = get_libero_env(lib_task, LIBERO_ENV_RESOLUTION, entry["environment_seed"])
    cfg, model, processor = load_wam(args.output)
    setattr(model.mot, "_fastwam_torch_compile_action", False)
    extractor = Extractor(cfg, model, processor)
    qgf_config = QGFConfig(**{key: value for key, value in deployment["qgf"].items() if key in QGFConfig.__dataclass_fields__})
    frozen_q = FrozenVisualQ(
        deployment["token_checkpoint"], [row["path"] for row in deployment["critic_checkpoints"]],
        "cuda", deployment["support_min"], deployment["support_max"], qgf_config,
    )
    scheduler = model.infer_action_scheduler
    prompt_cache = {}
    writer = None
    started = time.monotonic()
    steps = decisions = video_frames = 0
    success = done = False

    def frame(obs):
        images = get_libero_image(obs)
        return np.concatenate((images["image"], images["wrist_image"]), axis=1)

    def append_frame(obs):
        nonlocal video_frames
        writer.append_data(frame(obs)); video_frames += 1

    def predict(obs, state, seed, arm):
        wrapper = EqualComputeVisualQScheduler(scheduler, frozen_q, state, arm)
        model.infer_action_scheduler = wrapper
        cfg.seed = seed
        try:
            torch.cuda.synchronize(); tick = time.monotonic()
            action, *_ = _predict_action_chunk(
                obs, description, model, processor, cfg, action_horizon=32,
                input_h=224, input_w=448, model_device="cuda",
                profile_action_chunk_time=False, prompt_cache=prompt_cache,
            )
            torch.cuda.synchronize()
            if wrapper.final_sample is None:
                raise RuntimeError("scheduler did not expose final normalized action")
            return np.asarray(action, dtype=np.float32), wrapper.final_sample.numpy()[0], wrapper.trace, time.monotonic() - tick
        finally:
            model.infer_action_scheduler = scheduler

    try:
        env.reset(); obs = env.set_init_state(initial)
        actual = np.asarray(env.get_sim_state()).copy()
        if actual.shape != initial.shape or np.max(np.abs(actual - initial)) > 1e-6:
            raise RuntimeError("simulator restore exceeds frozen tolerance")
        writer = imageio.get_writer(args.output / "rollout.mp4", fps=24)
        append_frame(obs)
        for _ in range(30):
            obs, _, done, _ = env.step(get_libero_dummy_action())
            success = bool(env.check_success()); append_frame(obs)
        while steps < 700 and not done and not success:
            transition = args.output / f"transition_{decisions:04d}"
            transition.mkdir()
            save_rng(transition / "rng_before.npz", capture_rng())
            current = observation_payload(obs)
            before_state = np.asarray(env.get_sim_state()).copy()
            features = extractor(current, description)
            positions = torch.from_numpy(extractor.positions).to("cuda")
            state = frozen_q.encode(
                torch.from_numpy(features).unsqueeze(0).to("cuda"), positions,
                torch.from_numpy(proprio(current)).to("cuda"),
            )
            native, native_raw, guided, guided_raw, traces, latencies = [], [], [], [], [], []
            for seed in SEEDS:
                action, raw, shadow, elapsed = predict(current, state, seed, "candidate0")
                q_action, q_raw, q_trace, q_elapsed = predict(current, state, seed, "visual_qgf")
                native.append(action); native_raw.append(raw); guided.append(q_action); guided_raw.append(q_raw)
                traces.append({"native_shadow": shadow, "qgf": q_trace})
                latencies.append({"native_seconds": elapsed, "qgf_seconds": q_elapsed})
            native_t = torch.from_numpy(np.stack(native)).to("cuda")
            guided_t = torch.from_numpy(np.stack(guided)).to("cuda")
            native_raw_t = torch.from_numpy(np.stack(native_raw)).to("cuda")
            guided_raw_t = torch.from_numpy(np.stack(guided_raw)).to("cuda")
            decision = select_online_arm(
                arm=task_receipt["arm"], scene_key=task_receipt["scene_key"],
                decision_index=decisions, selection_seed=task_receipt["uniform_random_seed"],
                frozen_q=frozen_q, state=state, native_bank=native_t, guided_bank=guided_t,
                guidance_traces=tuple({"candidate": i, "native": traces[i]["native_shadow"], "qgf": traces[i]["qgf"]} for i in range(4)),
                native_score_bank=native_raw_t, guided_score_bank=guided_raw_t,
            )
            selected = decision.selected_actions[0].cpu().numpy()
            np.savez_compressed(
                transition / "decision.npz", features=features, positions=extractor.positions,
                token=state[0, :2048].detach().cpu().numpy(), proprio=proprio(current),
                native_bank=np.stack(native), native_raw=np.stack(native_raw),
                guided_bank=np.stack(guided), guided_raw=np.stack(guided_raw),
                selected_actions=selected,
            )
            receipt = dict(decision.receipt)
            receipt.update({"latencies": latencies, "state_sha256": array_hash(before_state),
                            "feature_sha256": array_hash(features), "token_sha256": array_hash(state[0, :2048].cpu().numpy())})
            write_json(transition / "decision.json", receipt)
            if not np.array_equal(before_state, np.asarray(env.get_sim_state())):
                raise RuntimeError("candidate computation changed simulator state")
            executed, rewards, dones, successes, sim_states = [], [], [], [], [before_state]
            for action in selected[:min(10, 700 - steps)]:
                committed = action.copy()
                obs, reward, done, _ = env.step(committed)
                executed.append(committed); rewards.append(float(reward)); success = bool(env.check_success())
                dones.append(bool(done)); successes.append(success); steps += 1
                sim_states.append(np.asarray(env.get_sim_state()).copy()); append_frame(obs)
                if done or success or steps >= 700: break
            np.savez_compressed(
                transition / "feedback.npz", executed_actions=np.stack(executed), rewards=np.asarray(rewards),
                environment_done=np.asarray(dones), success=np.asarray(successes), sim_states=np.stack(sim_states),
                commit_max_abs_error=np.asarray(float(np.max(np.abs(np.stack(executed) - selected[:len(executed)])))),
            )
            decisions += 1
        report = {
            "status": "SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE", "task_index": args.task_index,
            "scene_index": task_receipt["scene_index"], "arm": task_receipt["arm"],
            "steps": steps, "decisions": decisions, "official_success": bool(success),
            "environment_done": bool(done), "video_frames": video_frames,
            "wall_seconds": time.monotonic() - started,
            "online_registration_sha256": sha256(registration_path),
        }
        write_json(args.output / "REPORT.json", report)
        (args.output / report["status"]).touch()
        print(json.dumps(report, indent=2), flush=True)
    finally:
        if writer is not None: writer.close()
        env.close()


if __name__ == "__main__":
    main()
