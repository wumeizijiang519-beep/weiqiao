"""Build the frozen visual-token offline-RL corpus from audited real transitions."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from simplewam_visual_rl.models import TokenAutoencoder, TokenConfig


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def proprio(transition, prefix: str) -> np.ndarray:
    return np.concatenate([
        transition[f"{prefix}_robot0_eef_pos"],
        transition[f"{prefix}_robot0_eef_quat"],
        transition[f"{prefix}_robot0_gripper_qpos"],
    ]).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--features", type=Path, required=True)
    parser.add_argument("--token", type=Path, required=True)
    parser.add_argument("--token-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()
    if json.loads(args.token_audit.read_text()).get("status") != "SIMPLEWAM_RL_TOKEN_AUDIT_PASS":
        raise RuntimeError("audited token checkpoint required")
    checkpoint = torch.load(args.token, map_location="cpu", weights_only=False)
    model = TokenAutoencoder(TokenConfig(**checkpoint["model_config"]))
    model.load_state_dict(checkpoint["model"])
    model.to("cuda").eval()

    dataset = json.loads(args.dataset.read_text())
    entries = sorted(dataset["entries"], key=lambda row: row["episode_id"])
    columns = {name: [] for name in (
        "token", "next_token", "proprio", "next_proprio", "action_prefix",
        "rewards", "realized_length", "terminal", "group", "fold", "episode", "transition",
    )}
    for entry in entries:
        episode_id = entry["episode_id"]
        episode_dir = Path(entry["episode_directory"])
        with np.load(args.features / "blocks" / f"{episode_id}.npz", allow_pickle=False) as archive:
            features = np.asarray(archive["features"], dtype=np.float32)
            positions = torch.from_numpy(np.asarray(archive["positions"], dtype=np.float32)).to("cuda")
        encoded = []
        with torch.no_grad():
            for start in range(0, len(features), args.batch_size):
                batch = torch.from_numpy(features[start:start + args.batch_size]).to("cuda")
                encoded.append(model.encode(batch, positions).squeeze(1).cpu().numpy().astype(np.float16))
        tokens = np.concatenate(encoded)
        summary = json.loads((episode_dir / "summary.json").read_text())
        if len(tokens) != len(summary["transitions"]) + 1:
            raise RuntimeError(f"feature/transition mismatch for {episode_id}")
        for index, receipt in enumerate(summary["transitions"]):
            path = episode_dir / receipt["path"] / "transition.npz"
            with np.load(path, allow_pickle=False) as transition:
                selected = int(transition["selected_index"])
                actions = np.asarray(transition["candidates_raw_normalized"][selected, :10], dtype=np.float32)
                rewards = np.zeros(10, dtype=np.float32)
                realized = int(transition["actual_length"])
                rewards[:realized] = np.asarray(transition["rewards"][:realized], dtype=np.float32)
                columns["token"].append(tokens[index])
                columns["next_token"].append(tokens[index + 1])
                columns["proprio"].append(proprio(transition, "current"))
                columns["next_proprio"].append(proprio(transition, "next"))
                columns["action_prefix"].append(actions)
                columns["rewards"].append(rewards)
                columns["realized_length"].append(realized)
                columns["terminal"].append(bool(transition["terminal"]))
                columns["group"].append(entry["physical_input_group"])
                columns["fold"].append(int(entry["group_oof_fold"]))
                columns["episode"].append(episode_id)
                columns["transition"].append(index)

    args.output.mkdir(parents=True, exist_ok=False)
    corpus = args.output / "CORPUS.npz"
    np.savez_compressed(
        corpus,
        token=np.asarray(columns["token"], dtype=np.float16),
        next_token=np.asarray(columns["next_token"], dtype=np.float16),
        proprio=np.asarray(columns["proprio"], dtype=np.float32),
        next_proprio=np.asarray(columns["next_proprio"], dtype=np.float32),
        action_prefix=np.asarray(columns["action_prefix"], dtype=np.float32),
        rewards=np.asarray(columns["rewards"], dtype=np.float32),
        realized_length=np.asarray(columns["realized_length"], dtype=np.int16),
        terminal=np.asarray(columns["terminal"], dtype=np.bool_),
        group=np.asarray(columns["group"]),
        fold=np.asarray(columns["fold"], dtype=np.int8),
        episode=np.asarray(columns["episode"]),
        transition=np.asarray(columns["transition"], dtype=np.int16),
    )
    report = {
        "status": "SIMPLEWAM_VISUAL_RL_CRITIC_CORPUS_COMPLETE",
        "rows": len(columns["token"]),
        "episodes": len(entries),
        "physical_groups": len(set(columns["group"])),
        "token_dim": int(np.asarray(columns["token"]).shape[-1]),
        "planned_prefix_length": 10,
        "action_dim": 7,
        "realized_length_in_q_input": False,
        "corpus_sha256": sha256(corpus),
        "token_checkpoint_sha256": sha256(args.token),
        "dataset_sha256": sha256(args.dataset),
    }
    (args.output / "REPORT.json").write_text(json.dumps(report, indent=2))
    (args.output / report["status"]).touch()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
