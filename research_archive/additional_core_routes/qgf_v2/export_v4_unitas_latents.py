"""Export frozen UNITAS Florence latents for the admitted QGF-v4 Train32 set."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import torch

from probe_unitas_latent import pool_encoding
from unitas.models.encoders.florence import Florence2VLMEncoder


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prompt_for(data):
    instruction = str(data["instruction"].item()).strip().rstrip(".")
    return "The robot embodiment is a dual-arm ALOHA robot. " + instruction + ". Predict the successful robot trajectory."


def encode_episode(encoder, data, batch_size):
    count = int(data["head_rgb"].shape[0])
    if any(data[key].shape[0] != count for key in ("left_rgb", "right_rgb")):
        raise ValueError("camera lengths differ")
    prompt = prompt_for(data)
    chunks = []
    started = time.perf_counter()
    for begin in range(0, count, batch_size):
        end = min(begin + batch_size, count)
        images = np.stack([data["head_rgb"][begin:end], data["left_rgb"][begin:end], data["right_rgb"][begin:end]], axis=1)
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=encoder.device.type == "cuda"):
            encoded = encoder.encode_images_and_text(torch.from_numpy(images), [prompt] * (end - begin))
            pooled = pool_encoding(encoded).float().cpu().numpy()
        if pooled.shape != (end - begin, 9216) or not np.isfinite(pooled).all():
            raise ValueError("latent shape/finite contract failed")
        chunks.append(pooled.astype(np.float32, copy=False))
    return np.concatenate(chunks, axis=0), time.perf_counter() - started, prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--florence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    rank = int(os.environ.get("SLURM_PROCID", "0"))
    world = int(os.environ.get("SLURM_NTASKS", "1"))
    audit = json.loads(args.audit.read_text())
    if not audit.get("valid") or not audit.get("admits_critic_training") or len(audit.get("episodes", [])) != 32:
        raise ValueError("source Train32 audit is not admitted")
    if (audit.get("successes"), audit.get("failures")) != (25, 7):
        raise ValueError("frozen source outcome population changed")
    args.output.mkdir(parents=True, exist_ok=True)
    encoder = Florence2VLMEncoder(model_name=str(args.florence_dir.resolve()), device=args.device,
        dtype="fp32", local_files_only=True, attn_implementation="auto", image_size=768)
    rows = []
    for index, episode in enumerate(audit["episodes"]):
        if index % world != rank:
            continue
        path = Path(episode["file"])
        if sha256(path) != episode["sha256"]:
            raise ValueError("trajectory SHA changed: " + str(path))
        data = np.load(path, allow_pickle=False)
        seed = int(data["seed"].item())
        if seed != int(episode["seed"]) or bool(data["success"].item()) != bool(episode["success"]):
            raise ValueError("trajectory label identity changed")
        target = args.output / ("seed_%d.npz" % seed)
        if target.exists():
            raise FileExistsError(target)
        latent, elapsed, prompt = encode_episode(encoder, data, args.batch_size)
        temporary = args.output / (target.name + ".tmp.npz")
        np.savez_compressed(temporary, latent_states=latent, seed=np.asarray(seed, dtype=np.int64),
            success=np.asarray(bool(episode["success"])), source_sha256=np.asarray(episode["sha256"]), prompt=np.asarray(prompt))
        temporary.replace(target)
        rows.append({"seed": seed, "success": bool(episode["success"]), "observations": int(latent.shape[0]),
            "feature_dim": int(latent.shape[1]), "elapsed_seconds": elapsed,
            "source_sha256": episode["sha256"], "latent_sha256": sha256(target)})
    manifest = {"schema": "qgf_v4_unitas_latents_shard_v1", "rank": rank, "world": world,
        "source_audit_sha256": sha256(args.audit), "episodes": rows,
        "total_frames": sum(row["observations"] for row in rows),
        "total_elapsed_seconds": sum(row["elapsed_seconds"] for row in rows)}
    (args.output / ("manifest_rank%d.json" % rank)).write_text(json.dumps(manifest, indent=2) + "\n")
    (args.output / ("SHARD_%d_COMPLETE" % rank)).touch()


if __name__ == "__main__":
    main()

