"""Train one fixed seed/fold visual TwinQ/IQL worker and matched controls."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn
import torch.nn.functional as F


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mlp(input_dim: int, hidden: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Linear(input_dim, hidden), nn.LayerNorm(hidden), nn.SiLU(),
        nn.Linear(hidden, hidden), nn.SiLU(), nn.Linear(hidden, 1),
    )


class TwinQ(nn.Module):
    def __init__(self, input_dim: int, hidden: int):
        super().__init__()
        self.q1 = mlp(input_dim, hidden)
        self.q2 = mlp(input_dim, hidden)

    def forward(self, state, action):
        value = torch.cat((state, action.flatten(1)), dim=1)
        return torch.stack((self.q1(value).squeeze(1), self.q2(value).squeeze(1)))


class Value(nn.Module):
    def __init__(self, state_dim: int, hidden: int):
        super().__init__()
        self.net = mlp(state_dim, hidden)

    def forward(self, state):
        return self.net(state).squeeze(1)


def chunk_target(rewards, length, terminal, next_value, gamma):
    index = torch.arange(rewards.shape[1], device=rewards.device)
    discount = rewards.new_tensor(gamma).pow(index)
    observed = (rewards * discount * (index[None] < length[:, None])).sum(1)
    return observed + rewards.new_tensor(gamma).pow(length) * (~terminal).float() * next_value


def permutation_indices(groups, episodes, transitions, seed):
    result = np.arange(len(groups))
    for group in sorted(set(groups.tolist())):
        members = np.flatnonzero(groups == group)
        members = members[np.lexsort((transitions[members], episodes[members]))]
        if len(members) > 1:
            digest = hashlib.sha256(f"{seed}:{group}".encode()).digest()
            shift = 1 + int.from_bytes(digest[:4], "little") % (len(members) - 1)
            result[members] = np.roll(members, shift)
    return result


def monte_carlo_returns(rewards, lengths, terminals, episodes, transitions, gamma):
    returns = np.zeros(len(rewards), dtype=np.float32)
    for episode in sorted(set(episodes.tolist())):
        members = np.flatnonzero(episodes == episode)
        members = members[np.argsort(transitions[members])]
        future = 0.0
        for index in members[::-1]:
            m = int(lengths[index])
            observed = sum((gamma ** step) * float(rewards[index, step]) for step in range(m))
            future = observed + (0.0 if terminals[index] else gamma ** m * future)
            returns[index] = future
    return returns


def train_variant(name, state, next_state, actions, rewards, lengths, terminals,
                  train_index, heldout_index, permuted, mc_return, settings, seed, output):
    device = state.device
    action_input = actions.clone()
    if name == "state_only":
        action_input.zero_()
    elif name == "permutation":
        action_input[train_index] = actions[permuted[train_index]]
    state_dim = state.shape[1]
    action_dim = actions.shape[1] * actions.shape[2]
    critic = TwinQ(state_dim + action_dim, settings["hidden_dim"]).to(device)
    target = deepcopy(critic).eval().requires_grad_(False)
    value = Value(state_dim, settings["hidden_dim"]).to(device)
    optimizer = torch.optim.Adam(list(critic.parameters()) + list(value.parameters()), lr=settings["learning_rate"])
    generator = torch.Generator(device=device).manual_seed(seed)
    started = time.monotonic()
    last = {}
    for step in range(1, settings["updates"] + 1):
        pick = train_index[torch.randint(
            len(train_index), (settings["batch_size"],), generator=generator, device=device
        )]
        with torch.no_grad():
            target_q = target(state[pick], action_input[pick]).min(0).values
            next_v = value(next_state[pick])
            td = chunk_target(rewards[pick], lengths[pick], terminals[pick], next_v, settings["gamma"])
        current_q = critic(state[pick], action_input[pick])
        q_loss = F.mse_loss(current_q, td.unsqueeze(0).expand_as(current_q))
        current_v = value(state[pick])
        advantage = target_q - current_v
        weight = torch.where(advantage > 0, settings["expectile"], 1 - settings["expectile"])
        v_loss = (weight * advantage.square()).mean()
        loss = q_loss + v_loss
        if not torch.isfinite(loss):
            raise FloatingPointError(f"nonfinite {name} loss")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(list(critic.parameters()) + list(value.parameters()), 10.0, error_if_nonfinite=True)
        optimizer.step()
        with torch.no_grad():
            for source, destination in zip(critic.parameters(), target.parameters(), strict=True):
                destination.lerp_(source, settings["target_rate"])
        last = {"loss": float(loss.detach()), "q_loss": float(q_loss.detach()), "v_loss": float(v_loss.detach())}
        if step == 1 or step % 500 == 0 or step == settings["updates"]:
            print(json.dumps({"variant": name, "step": step, **last}), flush=True)
    critic.eval()
    with torch.no_grad():
        q_true = critic(state[heldout_index], actions[heldout_index]).min(0).values
        q_shuffled = critic(state[heldout_index], actions[permuted[heldout_index]]).min(0).values
    prediction = q_true.cpu().numpy().astype(np.float32)
    shuffled = q_shuffled.cpu().numpy().astype(np.float32)
    target_return = mc_return[heldout_index.cpu().numpy()]
    metrics = {
        "mc_mse": float(np.mean((prediction - target_return) ** 2)),
        "action_sensitivity": float(np.mean(np.abs(prediction - shuffled))),
        "elapsed_seconds": time.monotonic() - started,
        **last,
    }
    checkpoint = output / f"{name}.pt"
    torch.save({"critic": critic.cpu().state_dict(), "value": value.cpu().state_dict(), "settings": settings}, checkpoint)
    metrics["checkpoint_sha256"] = sha256(checkpoint)
    return metrics, prediction, shuffled, target_return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    if registration.get("status") != "SIMPLEWAM_VISUAL_IQL_WORKER_REGISTERED":
        raise RuntimeError("unexpected registration")
    args.output.mkdir(parents=True, exist_ok=False)
    seed, fold = int(registration["seed"]), int(registration["heldout_fold"])
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    with np.load(registration["corpus"], allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    state_np = np.concatenate((arrays["token"].astype(np.float32), arrays["proprio"]), axis=1)
    next_state_np = np.concatenate((arrays["next_token"].astype(np.float32), arrays["next_proprio"]), axis=1)
    device = torch.device("cuda")
    state = torch.from_numpy(state_np).to(device)
    next_state = torch.from_numpy(next_state_np).to(device)
    actions = torch.from_numpy(arrays["action_prefix"]).to(device)
    rewards = torch.from_numpy(arrays["rewards"]).to(device)
    lengths = torch.from_numpy(arrays["realized_length"].astype(np.int64)).to(device)
    terminals = torch.from_numpy(arrays["terminal"]).to(device)
    train_index = torch.from_numpy(np.flatnonzero(arrays["fold"] != fold)).long()
    heldout_index = torch.from_numpy(np.flatnonzero(arrays["fold"] == fold)).long().to(device)
    permutation = permutation_indices(arrays["group"], arrays["episode"], arrays["transition"], seed)
    permuted = torch.from_numpy(permutation).long().to(device)
    mc_return = monte_carlo_returns(arrays["rewards"], arrays["realized_length"], arrays["terminal"], arrays["episode"], arrays["transition"], registration["training"]["gamma"])
    train_index = train_index.to(device)
    predictions = {}
    metrics = {}
    for offset, name in enumerate(("proposed", "state_only", "permutation")):
        torch.manual_seed(seed + offset * 1000003); torch.cuda.manual_seed_all(seed + offset * 1000003)
        metrics[name], predictions[name], predictions[f"{name}_shuffled"], target_return = train_variant(
            name, state, next_state, actions, rewards, lengths, terminals,
            train_index, heldout_index, permuted, mc_return, registration["training"], seed + offset, args.output,
        )
    held = heldout_index.cpu().numpy()
    np.savez_compressed(
        args.output / "HELDOUT_PREDICTIONS.npz",
        row_index=held, group=arrays["group"][held], episode=arrays["episode"][held],
        transition=arrays["transition"][held], target_return=target_return,
        **predictions,
    )
    report = {
        "status": "SIMPLEWAM_VISUAL_IQL_WORKER_COMPLETE",
        "seed": seed, "heldout_fold": fold,
        "training_rows": int(len(train_index)), "heldout_rows": int(len(heldout_index)),
        "metrics": metrics,
        "predictions_sha256": sha256(args.output / "HELDOUT_PREDICTIONS.npz"),
        "registration_sha256": sha256(args.registration),
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.output / report["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
