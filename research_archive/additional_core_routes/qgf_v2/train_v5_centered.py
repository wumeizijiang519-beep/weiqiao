"""Fixed-final-step candidate-centered QGF-v5 OOF diagnostic."""

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_returns(rewards, steps, terminal):
    mask = np.arange(rewards.shape[1])[None] < steps[:, None]
    chunk = (rewards * mask).sum(axis=1).astype(np.float32)
    result = np.zeros_like(chunk)
    value = 0.0
    for index in range(len(chunk) - 1, -1, -1):
        value = float(chunk[index]) + (0.0 if terminal[index] else value)
        result[index] = value
    return result


class Critic(nn.Module):
    def __init__(self, state_only=False):
        super().__init__()
        self.state_only = state_only
        self.state = nn.Sequential(nn.Linear(9269, 512), nn.LayerNorm(512), nn.SiLU(),
                                   nn.Linear(512, 256), nn.LayerNorm(256), nn.SiLU())
        self.action = nn.Sequential(nn.Linear(320, 256), nn.LayerNorm(256), nn.SiLU())
        self.value = nn.Sequential(nn.Linear(256, 128), nn.SiLU(), nn.Linear(128, 1))
        self.advantage = nn.Sequential(nn.Linear(512, 256), nn.LayerNorm(256), nn.SiLU(),
                                       nn.Linear(256, 128), nn.SiLU(), nn.Linear(128, 1))

    def forward(self, states, candidates):
        state = self.state(states)
        value = self.value(state).squeeze(-1)
        if self.state_only:
            return value[:, None].expand(-1, 4)
        batch = candidates.shape[0]
        action = self.action(candidates.reshape(batch * 4, -1)).reshape(batch, 4, 256)
        tiled = state[:, None].expand(-1, 4, -1)
        advantage = self.advantage(torch.cat([tiled, action], dim=-1)).squeeze(-1)
        advantage = advantage - advantage.mean(dim=1, keepdim=True)
        return value[:, None] + advantage


def load_episode(stage, seed, scaler, device):
    candidate_path = stage / "v5_candidate_centered_v1" / f"candidates_seed{seed}.npz"
    latent_path = stage / "v4_unitas_latents_v1" / f"seed_{seed}.npz"
    audit = json.loads((stage / "v5_candidate_centered_v1" / "candidate_audit.json").read_text())
    row = next(item for item in audit["episodes"] if int(item["seed"]) == seed)
    source = Path(row["source_file"])
    with np.load(source, allow_pickle=False) as src, np.load(candidate_path, allow_pickle=False) as cand, \
            np.load(latent_path, allow_pickle=False) as lat:
        actions = cand["candidate_actions"].astype(np.float32)
        deviations = actions - actions.mean(axis=1, keepdims=True)
        spread = np.sqrt(np.mean(np.square(deviations), axis=1, keepdims=True))
        features = np.concatenate([deviations, np.broadcast_to(spread, deviations.shape)], axis=-1)
        features = (features - scaler["action_mean"]) / scaler["action_scale"]
        steps = np.append(src["replan_steps"], int(src["final_steps"])).astype(np.float32)
        remaining = (1.0 - steps / int(src["task_limit"]))[:, None]
        aux = np.concatenate([src["joint_positions"], src["tcp_pose"], remaining], axis=1)
        states = np.concatenate([lat["latent_states"], aux], axis=1)[:-1]
        states = (states - scaler["state_mean"]) / scaler["state_scale"]
        target = finite_returns(src["rewards"], src["executed_steps"], src["finite_horizon_terminal"])
        selected = cand["selected_index"].astype(np.int64)
    return {"seed": seed, "states": torch.as_tensor(states, device=device),
            "candidates": torch.as_tensor(features, device=device),
            "selected": torch.as_tensor(selected, device=device),
            "target": torch.as_tensor(target, device=device)}


def evaluate(model, episodes):
    model.eval()
    mses, margins = [], []
    with torch.no_grad():
        for episode in episodes:
            scores = model(episode["states"], episode["candidates"])
            chosen = scores.gather(1, episode["selected"][:, None]).squeeze(1)
            mses.append(float((chosen - episode["target"]).square().mean()))
            top = scores.topk(2, dim=1).values
            margins.append(float((top[:, 0] - top[:, 1]).mean()))
    return {"episode_equal_mse": float(np.mean(mses)), "episode_mse": mses,
            "mean_candidate_margin": float(np.mean(margins))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--kind", choices=["action", "state_only", "selected_permutation"], required=True)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    device = torch.device(args.device)
    data_root = args.stage / "v5_candidate_centered_v1" / "data"
    manifest_path = data_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    fold = manifest["folds"][args.fold]
    scaler_path = data_root / fold["scaler_file"]
    if sha(scaler_path) != fold["scaler_sha256"]:
        raise ValueError("scaler SHA mismatch")
    with np.load(scaler_path, allow_pickle=False) as raw:
        scaler = {key: raw[key].copy() for key in raw.files}
    train = [load_episode(args.stage, int(row["seed"]), scaler, device) for row in fold["train"]]
    validation = [load_episode(args.stage, int(row["seed"]), scaler, device) for row in fold["validation"]]
    if args.kind == "selected_permutation":
        for episode in train:
            permutation = np.random.default_rng(args.seed ^ episode["seed"]).permutation(len(episode["selected"]))
            episode["selected"] = episode["selected"][torch.as_tensor(permutation, device=device)]
    bootstrap = rng.integers(0, len(train), size=len(train))
    model = Critic(state_only=args.kind == "state_only").to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    args.output.mkdir(parents=True)
    config = {**vars(args), "stage": str(args.stage), "output": str(args.output),
              "bootstrap_episode_seeds": [train[int(i)]["seed"] for i in bootstrap],
              "manifest_sha256": sha(manifest_path)}
    (args.output / "config.json").write_text(json.dumps(config, indent=2, default=str) + "\n")
    started = time.monotonic()
    for step in range(1, args.steps + 1):
        model.train()
        draws = rng.choice(bootstrap, size=32, replace=True)
        rows = [(train[int(i)], int(rng.integers(len(train[int(i)]["target"])))) for i in draws]
        states = torch.stack([episode["states"][row] for episode, row in rows])
        candidates = torch.stack([episode["candidates"][row] for episode, row in rows])
        selected = torch.stack([episode["selected"][row] for episode, row in rows])
        target = torch.stack([episode["target"][row] for episode, row in rows])
        scores = model(states, candidates)
        prediction = scores.gather(1, selected[:, None]).squeeze(1)
        loss = (prediction - target).square().mean()
        if not torch.isfinite(loss):
            raise FloatingPointError("nonfinite loss")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0, error_if_nonfinite=True)
        optimizer.step()
    metrics = {"step": args.steps, "loss": float(loss.detach()),
               "elapsed_seconds": time.monotonic() - started, **evaluate(model, validation)}
    (args.output / "final_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    torch.save({"model": {k: v.detach().cpu() for k, v in model.state_dict().items()},
                "config": config, "validation": metrics}, args.output / "final.pt")
    (args.output / "COMPLETE").touch()


if __name__ == "__main__":
    main()
