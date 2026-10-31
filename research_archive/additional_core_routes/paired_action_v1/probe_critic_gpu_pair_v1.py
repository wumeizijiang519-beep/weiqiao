"""Critic-only CUDA qualification; no WAM, environment, or scientific data."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch


def run_device(index):
    device = torch.device(f"cuda:{index}")
    torch.cuda.set_device(device)
    torch.manual_seed(202641501)
    torch.cuda.manual_seed_all(202641501)
    x = torch.randn(1024, 256, device=device)
    target = torch.randn(1024, 1, device=device)
    model = torch.nn.Sequential(torch.nn.Linear(256, 256), torch.nn.SiLU(),
                                torch.nn.Linear(256, 1)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    losses = []
    torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(200):
        optimizer.zero_grad(set_to_none=True)
        loss = torch.nn.functional.mse_loss(model(x), target)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    torch.cuda.synchronize()
    vector = torch.cat([parameter.detach().flatten().cpu() for parameter in model.parameters()])
    props = torch.cuda.get_device_properties(device)
    return {"logical_device": index, "name": props.name,
            "total_memory": int(props.total_memory),
            "loss_initial": losses[0], "loss_final": losses[-1],
            "finite": bool(np.isfinite(losses).all() and torch.isfinite(vector).all()),
            "parameter_sha256": hashlib.sha256(vector.numpy().tobytes()).hexdigest(),
            "elapsed_seconds": time.perf_counter() - started,
            "peak_cuda_bytes": int(torch.cuda.max_memory_allocated(device))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if torch.cuda.device_count() != 2:
        raise RuntimeError(f"Expected exactly two allocated GPUs, got {torch.cuda.device_count()}")
    rows = [run_device(index) for index in range(2)]
    errors = []
    if not all(row["finite"] and row["loss_final"] < row["loss_initial"] for row in rows):
        errors.append("nonfinite_or_nonlearning")
    if rows[0]["parameter_sha256"] != rows[1]["parameter_sha256"]:
        errors.append("cross_device_determinism")
    result = {"status": "CRITIC_ONLY_GPU_PAIR_PASS" if not errors else "CRITIC_ONLY_GPU_PAIR_FAIL",
              "errors": errors, "devices": rows,
              "scientific_data_read": False, "wam_loaded": False,
              "robot_or_environment_actions": 0}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / result["status"]).touch()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
