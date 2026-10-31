"""Immutable position-aware Simple-WAM feature export for the frozen 288 corpus."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from simplewam_visual_rl.features import (
    SimpleWAMFeatureSpec,
    extract_current_video_features,
    prefill_video_cache_with_features,
)


OBS_KEYS = (
    "agentview_image",
    "robot0_eye_in_hand_image",
    "robot0_eef_pos",
    "robot0_eef_quat",
    "robot0_gripper_qpos",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Extractor:
    def __init__(self, cfg, model, processor):
        from experiments.libero.eval_libero_single import _get_num_video_frames

        self.cfg, self.model, self.processor = cfg, model, processor
        self.num_video_frames = _get_num_video_frames(cfg)
        self.spec = SimpleWAMFeatureSpec((29,), spatial_stride=4, num_views=2)
        self.prompt_cache: dict[str, tuple[torch.Tensor, torch.Tensor]] = {}
        self.positions = None

    @torch.no_grad()
    def __call__(self, observation: dict, description: str) -> np.ndarray:
        from experiments.libero.eval_libero_single import DEFAULT_PROMPT, _obs_to_model_input

        model = self.model
        image, proprio, _, _ = _obs_to_model_input(
            observation,
            cfg=self.cfg,
            processor=self.processor,
            width=448,
            height=224,
            device=model.device,
            dtype=model.torch_dtype,
        )
        prompt = DEFAULT_PROMPT.format(task=description)
        if prompt not in self.prompt_cache:
            self.prompt_cache[prompt] = model.encode_prompt(prompt, text_encoder_offload=True)
        base_context, base_mask = self.prompt_cache[prompt]
        context, context_mask = model._append_proprio_to_context(
            context=base_context.to(model.device),
            context_mask=base_mask.to(model.device),
            proprio=proprio.to(model.device, dtype=model.torch_dtype),
        )
        _, _, height, width = image.shape
        latent_t = (self.num_video_frames - 1) // model.vae.temporal_downsample_factor + 1
        latent_h = height // model.vae.upsampling_factor
        latent_w = width // model.vae.upsampling_factor
        generator = torch.Generator(device="cpu").manual_seed(202644001)
        latents = torch.randn(
            (1, model.vae.model.z_dim, latent_t, latent_h, latent_w),
            generator=generator,
            device="cpu",
            dtype=torch.float32,
        ).to(model.device, dtype=model.torch_dtype)
        latents[:, :, :1] = model._encode_input_image_latents_tensor(
            input_image=image.to(model.device, dtype=model.torch_dtype), tiled=False
        )
        timesteps, _ = model.infer_video_scheduler.build_inference_schedule(
            num_inference_steps=10,
            device=model.device,
            dtype=latents.dtype,
            shift_override=None,
        )
        video_pre = model.video_expert.pre_dit(
            x=latents,
            timestep=timesteps[0].unsqueeze(0),
            context=context,
            context_mask=context_mask,
            action=None,
            fuse_vae_embedding_in_latents=bool(
                getattr(model.video_expert, "fuse_vae_embedding_in_latents", False)
            ),
        )
        grid = tuple(int(v) for v in video_pre["meta"]["grid_size"])
        video_count = int(video_pre["tokens"].shape[1])
        attention_mask = model._build_mot_attention_mask(
            video_seq_len=video_count,
            action_seq_len=32,
            video_tokens_per_frame=int(video_pre["meta"]["tokens_per_frame"]),
            device=video_pre["tokens"].device,
        )
        _, captured = prefill_video_cache_with_features(
            model.mot,
            video_tokens=video_pre["tokens"],
            video_freqs=video_pre["freqs"],
            video_t_mod=video_pre["t_mod"],
            video_context_payload={"context": video_pre["context"], "mask": video_pre["context_mask"]},
            video_attention_mask=attention_mask[:video_count, :video_count],
            capture_layers=set(self.spec.layers),
        )
        features, positions = extract_current_video_features(captured, grid, self.spec)
        positions = positions.cpu().numpy().astype(np.float32)
        if self.positions is None:
            self.positions = positions
        elif not np.array_equal(self.positions, positions):
            raise RuntimeError("position contract changed during corpus export")
        return features[0].cpu().numpy().astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    if registration.get("status") != "SIMPLEWAM_VISUAL_FEATURE_EXPORT_REGISTERED":
        raise RuntimeError("unexpected export registration")
    if sha(Path(registration["dataset_result"])) != registration["dataset_sha256"]:
        raise RuntimeError("dataset certificate changed")
    if sha(Path(registration["input_index"])) != registration["input_index_sha256"]:
        raise RuntimeError("input observation index changed")
    root = Path(__file__).parent
    for name, digest in registration["source_sha256"].items():
        path = root / name if name != "wam_runtime.py" else Path(registration["wam_runtime"])
        if sha(path) != digest:
            raise RuntimeError(f"registered source changed: {name}")

    dataset = json.loads(Path(registration["dataset_result"]).read_text())
    index = json.loads(Path(registration["input_index"]).read_text())
    entries = {row["episode_id"]: row for row in dataset["entries"]}
    receipts = {row["episode_id"]: row for row in index["episodes"]}
    if set(entries) != set(receipts) or len(entries) != 288:
        raise RuntimeError("frozen 288 episode population differs")
    run = Path(registration["run_directory"])
    blocks = run / "blocks"
    run.mkdir(parents=True, exist_ok=False)
    blocks.mkdir()

    from wam_runtime import load_wam

    cfg, model, processor = load_wam(run)
    setattr(model.mot, "_fastwam_torch_compile_action", False)
    extractor = Extractor(cfg, model, processor)
    started = time.monotonic()
    completed = 0
    for episode_id in sorted(entries):
        entry, receipt = entries[episode_id], receipts[episode_id]
        episode = Path(entry["episode_directory"])
        runtime = episode / "runtime_config.json"
        description = json.loads(runtime.read_text())["task_description"]
        hashes = receipt["observation_file_sha256"]
        values, timings = [], []
        for number, expected in enumerate(hashes):
            path = episode / f"observation_{number:04d}.npz"
            if sha(path) != expected:
                raise RuntimeError(f"observation receipt changed: {episode_id}/{number}")
            with np.load(path, allow_pickle=False) as archive:
                observation = {key: archive[key].copy() for key in OBS_KEYS}
            tick = time.monotonic()
            values.append(extractor(observation, description))
            torch.cuda.synchronize()
            timings.append(time.monotonic() - tick)
        array_path = blocks / f"{episode_id}.npz"
        np.savez_compressed(array_path, features=np.stack(values), positions=extractor.positions)
        block_report = {
            "episode_id": episode_id,
            "episode_directory": str(episode),
            "observation_sha256": hashes,
            "observation_count": len(hashes),
            "feature_shape": list(np.stack(values).shape),
            "positions_shape": list(extractor.positions.shape),
            "feature_file": array_path.name,
            "feature_file_sha256": sha(array_path),
            "encode_seconds": timings,
        }
        (blocks / f"{episode_id}.json").write_text(json.dumps(block_report, indent=2))
        completed += 1
        (run / "LAST_COMPLETE_EPISODE").write_text(episode_id + "\n")
        print(json.dumps({"episode": episode_id, "completed": completed, "observations": len(hashes), "p50_seconds": float(np.median(timings))}), flush=True)
    report = {
        "status": "SIMPLEWAM_VISUAL_FEATURE_EXPORT_COMPLETE",
        "episodes": completed,
        "feature_spec": {"layers": [29], "spatial_stride": 4, "num_views": 2},
        "position_sha256": hashlib.sha256(np.ascontiguousarray(extractor.positions).tobytes()).hexdigest(),
        "wall_seconds": time.monotonic() - started,
        "robot_actions_executed": 0,
        "critic_updates": 0,
    }
    (run / "REPORT.json").write_text(json.dumps(report, indent=2))
    (run / report["status"]).touch()


if __name__ == "__main__":
    main()
