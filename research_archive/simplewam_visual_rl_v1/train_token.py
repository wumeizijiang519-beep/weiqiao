"""Outcome-blind reconstruction training for the Simple-WAM RL token."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
import torch.nn.functional as F

from simplewam_visual_rl.models import TokenAutoencoder, TokenConfig


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    if registration.get("status") != "SIMPLEWAM_RL_TOKEN_TRAINING_REGISTERED":
        raise RuntimeError("unexpected token registration")
    args.output.mkdir(parents=True, exist_ok=False)
    seed = int(registration["seed"])
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)

    export = Path(registration["feature_export"])
    audit = json.loads(Path(registration["feature_audit"]).read_text())
    if audit.get("status") != "SIMPLEWAM_VISUAL_FEATURE_EXPORT_AUDIT_PASS":
        raise RuntimeError("qualified visual feature export required")
    dataset = json.loads(Path(registration["dataset_result"]).read_text())
    group_by_episode = {row["episode_id"]: row["physical_input_group"] for row in dataset["entries"]}
    validation_groups = set(registration["validation_groups"])
    train_features, validation_features = [], []
    positions = None
    for episode_id in sorted(group_by_episode):
        with np.load(export / "blocks" / f"{episode_id}.npz", allow_pickle=False) as archive:
            values = np.asarray(archive["features"], dtype=np.float32)
            current_positions = np.asarray(archive["positions"], dtype=np.float32)
        if positions is None:
            positions = current_positions
        elif not np.array_equal(positions, current_positions):
            raise RuntimeError("position grid changed")
        target = validation_features if group_by_episode[episode_id] in validation_groups else train_features
        target.append(values)
    train = torch.from_numpy(np.concatenate(train_features)).to("cuda")
    validation = torch.from_numpy(np.concatenate(validation_features)).to("cuda")
    positions_t = torch.from_numpy(positions).to("cuda")
    config = TokenConfig(**registration["model"])
    model = TokenAutoencoder(config).to("cuda")
    optimizer = torch.optim.Adam(model.parameters(), lr=float(registration["learning_rate"]))
    generator = torch.Generator(device="cpu").manual_seed(seed)
    batch_size = int(registration["batch_size"])
    started = time.monotonic()
    model.train()
    last_loss = None
    for step in range(1, int(registration["updates"]) + 1):
        index = torch.randint(len(train), (batch_size,), generator=generator)
        batch = train[index.to(train.device)]
        optimizer.zero_grad(set_to_none=True)
        _, reconstructed = model(batch, positions_t)
        target = F.layer_norm(batch.float(), (batch.shape[-1],))
        loss = F.mse_loss(reconstructed, target)
        if not torch.isfinite(loss):
            raise FloatingPointError("nonfinite token loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0, error_if_nonfinite=True)
        optimizer.step()
        last_loss = float(loss.detach())
        if step == 1 or step % 500 == 0 or step == registration["updates"]:
            print(json.dumps({"step": step, "reconstruction_loss": last_loss}), flush=True)
    model.eval()
    with torch.no_grad():
        total, count = 0.0, 0
        for start in range(0, len(validation), batch_size):
            batch = validation[start:start + batch_size]
            _, reconstructed = model(batch, positions_t)
            target = F.layer_norm(batch.float(), (batch.shape[-1],))
            total += float(F.mse_loss(reconstructed, target, reduction="sum"))
            count += target.numel()
    payload = {
        "format_version": 1,
        "stage": "simplewam_visual_rl_token",
        "model_config": asdict(config),
        "model": model.cpu().state_dict(),
        "registration_sha256": sha(args.registration),
        "training_rows": len(train),
        "validation_rows": len(validation),
        "updates": registration["updates"],
        "seed": seed,
    }
    checkpoint = args.output / "TOKEN.pt"
    torch.save(payload, checkpoint)
    report = {
        "status": "SIMPLEWAM_RL_TOKEN_TRAINING_COMPLETE",
        "checkpoint_sha256": sha(checkpoint),
        "final_train_reconstruction_mse": last_loss,
        "validation_reconstruction_mse": total / count,
        "elapsed_seconds": time.monotonic() - started,
        "reward_fields_read": 0,
        "success_fields_read": 0,
        "critic_updates": 0,
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.output / report["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
