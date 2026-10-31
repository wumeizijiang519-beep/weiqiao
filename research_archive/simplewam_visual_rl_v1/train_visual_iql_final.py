"""Train one fixed-seed full-data final TwinQ/IQL critic."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
import torch.nn.functional as F

from train_visual_iql_fold import (
    TwinQ,
    Value,
    chunk_target,
    monte_carlo_returns,
    permutation_indices,
    sha256,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    if registration.get("status") != "SIMPLEWAM_VISUAL_IQL_FINAL_REGISTERED":
        raise RuntimeError("unexpected final critic registration")
    corpus = Path(registration["corpus"])
    if sha256(corpus) != registration["corpus_sha256"]:
        raise RuntimeError("corpus hash mismatch")
    args.output.mkdir(parents=True, exist_ok=False)

    seed = int(registration["seed"])
    settings = registration["training"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)

    with np.load(corpus, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    if len(arrays["token"]) != registration["required_rows"]:
        raise RuntimeError("row count mismatch")
    state_np = np.concatenate((arrays["token"].astype(np.float32), arrays["proprio"]), axis=1)
    next_state_np = np.concatenate((arrays["next_token"].astype(np.float32), arrays["next_proprio"]), axis=1)
    device = torch.device("cuda")
    state = torch.from_numpy(state_np).to(device)
    next_state = torch.from_numpy(next_state_np).to(device)
    actions = torch.from_numpy(arrays["action_prefix"]).to(device)
    rewards = torch.from_numpy(arrays["rewards"]).to(device)
    lengths = torch.from_numpy(arrays["realized_length"].astype(np.int64)).to(device)
    terminals = torch.from_numpy(arrays["terminal"]).to(device)

    action_size = actions.shape[1] * actions.shape[2]
    critic = TwinQ(state.shape[1] + action_size, settings["hidden_dim"]).to(device)
    target = deepcopy(critic).eval().requires_grad_(False)
    value = Value(state.shape[1], settings["hidden_dim"]).to(device)
    optimizer = torch.optim.Adam(
        list(critic.parameters()) + list(value.parameters()),
        lr=settings["learning_rate"],
    )
    generator = torch.Generator(device=device).manual_seed(seed)
    started = time.monotonic()
    last = {}
    for step in range(1, settings["updates"] + 1):
        pick = torch.randint(len(state), (settings["batch_size"],), generator=generator, device=device)
        with torch.no_grad():
            target_q = target(state[pick], actions[pick]).min(0).values
            next_v = value(next_state[pick])
            td = chunk_target(rewards[pick], lengths[pick], terminals[pick], next_v, settings["gamma"])
        current_q = critic(state[pick], actions[pick])
        q_loss = F.mse_loss(current_q, td.unsqueeze(0).expand_as(current_q))
        current_v = value(state[pick])
        advantage = target_q - current_v
        weight = torch.where(advantage > 0, settings["expectile"], 1 - settings["expectile"])
        v_loss = (weight * advantage.square()).mean()
        loss = q_loss + v_loss
        if not torch.isfinite(loss):
            raise FloatingPointError("nonfinite final critic loss")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(critic.parameters()) + list(value.parameters()),
            settings["parameter_grad_norm"],
            error_if_nonfinite=True,
        )
        optimizer.step()
        with torch.no_grad():
            for source, destination in zip(critic.parameters(), target.parameters()):
                destination.lerp_(source, settings["target_rate"])
        last = {
            "loss": float(loss.detach()),
            "q_loss": float(q_loss.detach()),
            "v_loss": float(v_loss.detach()),
        }
        if step == 1 or step % 1000 == 0 or step == settings["updates"]:
            print(json.dumps({"seed": seed, "step": step, **last}), flush=True)

    critic.eval()
    permutation = permutation_indices(
        arrays["group"], arrays["episode"], arrays["transition"], seed
    )
    mc_return = monte_carlo_returns(
        arrays["rewards"], arrays["realized_length"], arrays["terminal"],
        arrays["episode"], arrays["transition"], settings["gamma"],
    )
    prediction_parts = []
    shuffled_parts = []
    batch = 512
    with torch.no_grad():
        for start in range(0, len(state), batch):
            stop = min(start + batch, len(state))
            prediction_parts.append(critic(state[start:stop], actions[start:stop]).min(0).values.cpu())
            perm = torch.from_numpy(permutation[start:stop]).long().to(device)
            shuffled_parts.append(critic(state[start:stop], actions[perm]).min(0).values.cpu())
    prediction = torch.cat(prediction_parts).numpy().astype(np.float32)
    shuffled = torch.cat(shuffled_parts).numpy().astype(np.float32)
    checkpoint = args.output / "FINAL_CRITIC.pt"
    torch.save(
        {
            "critic": critic.cpu().state_dict(),
            "value": value.cpu().state_dict(),
            "settings": settings,
            "seed": seed,
            "full_training_rows": len(state),
            "corpus_sha256": registration["corpus_sha256"],
            "token_checkpoint_sha256": registration["token_checkpoint_sha256"],
        },
        checkpoint,
    )
    metrics = {
        "mc_mse_full_training": float(np.mean((prediction - mc_return) ** 2)),
        "action_sensitivity_full_training": float(np.mean(np.abs(prediction - shuffled))),
        "q_mean": float(prediction.mean()),
        "q_std": float(prediction.std()),
        "elapsed_seconds": time.monotonic() - started,
        **last,
    }
    report = {
        "status": "SIMPLEWAM_VISUAL_IQL_FINAL_COMPLETE",
        "seed": seed,
        "training_rows": len(state),
        "fixed_final_step": settings["updates"],
        "metrics_are_checkpoint_selection_inputs": False,
        "metrics": metrics,
        "checkpoint_sha256": sha256(checkpoint),
        "registration_sha256": sha256(args.registration),
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    (args.output / report["status"]).touch()
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

