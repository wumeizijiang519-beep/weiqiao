"""Zero-action live-runtime gate before any held-out online execution."""

import argparse
import hashlib
import json
from pathlib import Path
import random

import numpy as np
import torch

from export_features import Extractor
from simplewam_visual_rl.deployment import FrozenVisualQ, QGFConfig
from simplewam_visual_rl.scheduler import EqualComputeVisualQScheduler


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def proprio(obs):
    return np.concatenate((obs["robot0_eef_pos"], obs["robot0_eef_quat"], obs["robot0_gripper_qpos"])).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = args.root / "simplewam_visual_rl_v1"
    registration_path = base / "online_registration_v1/REGISTRATION.json"
    registration = json.loads(registration_path.read_text())
    deployment_path = Path(registration["deployment_registration"])
    deployment = json.loads(deployment_path.read_text())
    cohort = json.loads(Path(registration["cohort_manifest"]).read_text())
    entry = cohort["partitions"]["validation"][0]
    args.output.mkdir(parents=True, exist_ok=False)

    from experiments.libero.eval_libero_single import _predict_action_chunk
    from experiments.libero.libero_utils import LIBERO_ENV_RESOLUTION, get_libero_env
    from libero.libero import benchmark
    from wam_runtime import file_sha, load_wam

    for key, digest_key in (("initial_state_path", "initial_file_sha256"), ("bddl_path", "bddl_sha256")):
        if file_sha(entry[key]) != entry[digest_key]:
            raise RuntimeError("held-out scene asset changed")
    states = np.asarray(torch.load(entry["initial_state_path"], map_location="cpu", weights_only=False))
    initial = np.asarray(states[entry["initial_state_index"]], dtype="<f8")
    if hashlib.sha256(initial.tobytes()).hexdigest() != entry["state_sha256"]:
        raise RuntimeError("held-out initial state changed")
    random.seed(entry["environment_seed"]); np.random.seed(entry["environment_seed"]); torch.manual_seed(entry["environment_seed"])
    suite = benchmark.get_benchmark_dict()["libero_10"]()
    task = suite.get_task(entry["task_id"])
    env, description = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry["environment_seed"])
    cfg, model, processor = load_wam(args.output)
    setattr(model.mot, "_fastwam_torch_compile_action", False)
    try:
        env.reset()
        obs = env.set_init_state(initial)
        restored = np.asarray(env.get_sim_state()).copy()
        restore_error = float(np.max(np.abs(restored - initial)))
        if restore_error > 1e-6:
            raise RuntimeError("live simulator restore exceeds frozen tolerance")
        extractor = Extractor(cfg, model, processor)
        feature_a = extractor(obs, description)
        feature_b = extractor(obs, description)
        feature_error = float(np.max(np.abs(feature_a - feature_b)))
        if feature_error != 0.0:
            raise RuntimeError("live layer29 features are not bitwise repeatable")
        qgf_config = QGFConfig(**{
            key: value for key, value in deployment["qgf"].items()
            if key in QGFConfig.__dataclass_fields__
        })
        q = FrozenVisualQ(
            deployment["token_checkpoint"], [row["path"] for row in deployment["critic_checkpoints"]],
            "cuda", deployment["support_min"], deployment["support_max"], qgf_config,
        )
        positions = torch.from_numpy(extractor.positions).to("cuda")
        state = q.encode(torch.from_numpy(feature_a).unsqueeze(0).to("cuda"), positions, torch.from_numpy(proprio(obs)).to("cuda"))
        scheduler = model.infer_action_scheduler
        prompt_cache = {}

        def predict(arm):
            wrapper = EqualComputeVisualQScheduler(scheduler, q, state, arm)
            model.infer_action_scheduler = wrapper
            cfg.seed = 10000
            try:
                action, *_ = _predict_action_chunk(obs, description, model, processor, cfg, action_horizon=32, input_h=224, input_w=448, model_device="cuda", prompt_cache=prompt_cache)
                return np.asarray(action, dtype=np.float32), wrapper.final_sample.numpy()[0], wrapper.trace
            finally:
                model.infer_action_scheduler = scheduler

        native_a, raw_a, trace_a = predict("candidate0")
        native_b, raw_b, trace_b = predict("candidate0")
        native_error = float(np.max(np.abs(native_a - native_b)))
        raw_error = float(np.max(np.abs(raw_a - raw_b)))
        if max(native_error, raw_error) > 1e-6:
            raise RuntimeError("live Simple-WAM replay exceeds frozen tolerance")
        _, _, qgf_trace = predict("visual_qgf")
        if not any(row.get("shadow_computed") for row in trace_a) or not any(row.get("guidance_committed") for row in qgf_trace):
            raise RuntimeError("QGF scheduler integration did not execute")
        if not np.array_equal(restored, np.asarray(env.get_sim_state())):
            raise RuntimeError("zero-action gate changed simulator state")
    finally:
        env.close()

    report = {
        "status": "SIMPLEWAM_VISUAL_QGF_WAM_COMPATIBILITY_PASS",
        "online_registration_sha256": sha256(registration_path),
        "deployment_registration_sha256": sha256(deployment_path),
        "scene_index": 0, "robot_actions_executed": 0,
        "initial_state_max_abs_error": restore_error,
        "feature_repeat_max_abs_error": feature_error,
        "native_replay_max_abs_error": native_error,
        "raw_replay_max_abs_error": raw_error,
        "candidate0_shadow_steps": len(trace_a), "qgf_guided_steps": len(qgf_trace),
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / report["status"]).touch()
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
