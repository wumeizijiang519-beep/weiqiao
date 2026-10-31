"""Bounded probe for frozen UNITAS Florence image-language features."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from unitas.models.encoders.florence import Florence2VLMEncoder


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pool_encoding(encoded):
    tensors = [
        encoded.visual_tokens.mean(dim=1),
        encoded.visual_tokens.float().std(dim=1, unbiased=False),
        encoded.language_tokens.mean(dim=1),
    ]
    images = encoded.image_features
    for view in range(images.shape[1]):
        tensors.append(images[:, view].mean(dim=1))
        tensors.append(images[:, view].float().std(dim=1, unbiased=False))
    return torch.cat([value.float() for value in tensors], dim=-1)


def encode(encoder, images, prompt):
    started = time.perf_counter()
    with torch.inference_mode(), torch.autocast(
        "cuda", dtype=torch.bfloat16, enabled=encoder.device.type == "cuda"
    ):
        encoded = encoder.encode_images_and_text(images, [prompt])
        pooled = pool_encoding(encoded)
    if pooled.ndim != 2 or pooled.shape[0] != 1:
        raise ValueError("pooled feature contract failed")
    array = pooled[0].cpu().numpy().astype(np.float32, copy=False)
    if not np.isfinite(array).all():
        raise ValueError("nonfinite UNITAS feature")
    return array, time.perf_counter() - started, {
        "vlm_features": list(encoded.vlm_features.shape),
        "visual_tokens": list(encoded.visual_tokens.shape),
        "language_tokens": list(encoded.language_tokens.shape),
        "image_features": list(encoded.image_features.shape),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--florence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("refusing to overwrite probe output")
    data = np.load(args.trajectory, allow_pickle=False)
    required = {"head_rgb", "left_rgb", "right_rgb", "instruction", "seed"}
    if not required.issubset(data.files):
        raise ValueError("trajectory lacks required RGB/instruction fields")
    count = int(data["head_rgb"].shape[0])
    if count < 3 or any(data[key].shape[0] != count for key in ("left_rgb", "right_rgb")):
        raise ValueError("invalid trajectory camera lengths")
    instruction = str(data["instruction"].item()).strip().rstrip(".")
    prompt = (
        "The robot embodiment is a dual-arm ALOHA robot. "
        + instruction
        + ". Predict the successful robot trajectory."
    )
    encoder = Florence2VLMEncoder(
        model_name=str(args.florence_dir.resolve()),
        device=args.device,
        dtype="fp32",
        local_files_only=True,
        attn_implementation="auto",
        image_size=768,
    )
    indices = sorted({0, count // 2, count - 1})
    rows = []
    features = []
    first = None
    for index in indices:
        images = torch.from_numpy(
            np.stack(
                [data["head_rgb"][index], data["left_rgb"][index], data["right_rgb"][index]],
                axis=0,
            )[None]
        )
        feature, elapsed, shapes = encode(encoder, images, prompt)
        features.append(feature)
        if first is None:
            first = feature.copy()
            repeated, repeat_elapsed, repeat_shapes = encode(encoder, images, prompt)
            repeat_error = float(np.max(np.abs(first - repeated)))
            if repeat_shapes != shapes:
                raise ValueError("repeat feature shapes changed")
        else:
            repeat_elapsed = None
            repeat_error = None
        rows.append(
            {
                "frame": index,
                "elapsed_seconds": elapsed,
                "repeat_elapsed_seconds": repeat_elapsed,
                "repeat_max_abs_error": repeat_error,
                "feature_dim": int(feature.size),
                "feature_l2": float(np.linalg.norm(feature)),
                "feature_mean": float(feature.mean()),
                "feature_std": float(feature.std()),
                "shapes": shapes,
            }
        )
    args.output.mkdir(parents=True)
    np.save(args.output / "features.npy", np.stack(features))
    result = {
        "schema": "qgf_v3_unitas_latent_probe_v1",
        "trajectory": str(args.trajectory),
        "trajectory_sha256": sha256(args.trajectory),
        "seed": int(data["seed"].item()),
        "frames": indices,
        "prompt": prompt,
        "rows": rows,
        "feature_file_sha256": sha256(args.output / "features.npy"),
        "passed": all(row["feature_dim"] > 0 for row in rows)
        and rows[0]["repeat_max_abs_error"] == 0.0,
        "note": "Engineering feasibility only; no action-value or robot-gain evidence.",
    }
    (args.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "COMPLETE").write_text("\n")


if __name__ == "__main__":
    main()
