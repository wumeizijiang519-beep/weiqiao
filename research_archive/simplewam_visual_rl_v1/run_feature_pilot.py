"""Read-only Simple-WAM visual hidden-state pilot on one archived observation."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from simplewam_visual_rl.features import (
    SimpleWAMFeatureSpec,
    extract_current_video_features,
    prefill_video_cache_with_features,
)


def digest_bytes(value: torch.Tensor) -> str:
    # NumPy has no native bfloat16 dtype. Hash a canonical float32 copy while
    # leaving the frozen model tensor and feature values untouched.
    array = value.detach().to(device="cpu", dtype=torch.float32).contiguous().numpy()
    return hashlib.sha256(array.tobytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    args.run.mkdir(parents=True, exist_ok=False)

    from experiments.libero.eval_libero_single import DEFAULT_PROMPT, _get_num_video_frames, _obs_to_model_input
    from wam_runtime import file_sha, load_wam

    input_sha = file_sha(args.observation)
    with np.load(args.observation, allow_pickle=False) as archive:
        observation = {key: archive[key].copy() for key in (
            "agentview_image",
            "robot0_eye_in_hand_image",
            "robot0_eef_pos",
            "robot0_eef_quat",
            "robot0_gripper_qpos",
        )}
    cfg, model, processor = load_wam(args.run)
    # Hidden-state export must use the transparent eager prefill path.
    setattr(model.mot, "_fastwam_torch_compile_action", False)
    image, proprio, _, _ = _obs_to_model_input(
        observation,
        cfg=cfg,
        processor=processor,
        width=448,
        height=224,
        device=model.device,
        dtype=model.torch_dtype,
    )
    prompt = DEFAULT_PROMPT.format(task=args.description)
    context, context_mask = model.encode_prompt(prompt, text_encoder_offload=True)
    base_context = context.detach().clone()
    context, context_mask = model._append_proprio_to_context(
        context=context.to(model.device),
        context_mask=context_mask.to(model.device),
        proprio=proprio.to(model.device, dtype=model.torch_dtype),
    )

    num_video_frames = _get_num_video_frames(cfg)
    _, _, height, width = image.shape
    latent_t = (num_video_frames - 1) // model.vae.temporal_downsample_factor + 1
    latent_h = height // model.vae.upsampling_factor
    latent_w = width // model.vae.upsampling_factor
    generator = torch.Generator(device="cpu").manual_seed(202644001)
    latents = torch.randn(
        (1, model.vae.model.z_dim, latent_t, latent_h, latent_w),
        generator=generator,
        device="cpu",
        dtype=torch.float32,
    ).to(model.device, dtype=model.torch_dtype)
    current = model._encode_input_image_latents_tensor(
        input_image=image.to(model.device, dtype=model.torch_dtype), tiled=False
    )
    latents[:, :, :1] = current
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
    video_seq_len = int(video_pre["tokens"].shape[1])
    attention_mask = model._build_mot_attention_mask(
        video_seq_len=video_seq_len,
        action_seq_len=32,
        video_tokens_per_frame=int(video_pre["meta"]["tokens_per_frame"]),
        device=video_pre["tokens"].device,
    )

    spec = SimpleWAMFeatureSpec((29,), spatial_stride=4, num_views=2)
    kwargs = dict(
        video_tokens=video_pre["tokens"],
        video_freqs=video_pre["freqs"],
        video_t_mod=video_pre["t_mod"],
        video_context_payload={"context": video_pre["context"], "mask": video_pre["context_mask"]},
        video_attention_mask=attention_mask[:video_seq_len, :video_seq_len],
        capture_layers=set(spec.layers),
    )
    with torch.no_grad():
        cache_a, captured_a = prefill_video_cache_with_features(model.mot, **kwargs)
        cache_b, captured_b = prefill_video_cache_with_features(model.mot, **kwargs)
        features_a, positions_a = extract_current_video_features(captured_a, grid, spec)
        features_b, positions_b = extract_current_video_features(captured_b, grid, spec)
    repeat_error = float((features_a - features_b).abs().max().cpu())
    position_error = float((positions_a - positions_b).abs().max().cpu())
    if repeat_error != 0.0 or position_error != 0.0:
        raise RuntimeError("Simple-WAM visual feature extraction is not bitwise repeatable")
    if len(cache_a) != model.mot.num_layers or len(cache_b) != model.mot.num_layers:
        raise RuntimeError("video prefill cache is incomplete")
    if file_sha(args.observation) != input_sha:
        raise RuntimeError("archived observation changed during extraction")

    np.savez_compressed(
        args.run / "FEATURES.npz",
        features=features_a.cpu().numpy().astype(np.float32),
        positions=positions_a.cpu().numpy().astype(np.float32),
    )
    report = {
        "status": "SIMPLEWAM_VISUAL_FEATURE_PILOT_PASS",
        "backbone": "Simple-WAM",
        "benchmark": "LIBERO",
        "tau0_runtime_dependency": False,
        "observation": str(args.observation),
        "observation_sha256": input_sha,
        "description": args.description,
        "feature_spec": {"layers": list(spec.layers), "spatial_stride": spec.spatial_stride, "num_views": spec.num_views},
        "grid_size": list(grid),
        "feature_shape": list(features_a.shape),
        "position_shape": list(positions_a.shape),
        "feature_sha256": digest_bytes(features_a),
        "position_sha256": digest_bytes(positions_a),
        "prompt_context_sha256": digest_bytes(base_context),
        "repeat_max_abs_error": repeat_error,
        "position_repeat_max_abs_error": position_error,
        "robot_actions_executed": 0,
        "critic_updates": 0,
    }
    (args.run / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.run / report["status"]).touch()
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
