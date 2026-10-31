"""Prepare immutable four-fold candidate-centered QGF-v5 manifests and scalers."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def episode_arrays(row, latent_root):
    seed = int(row["seed"])
    source = Path(row["source_file"])
    candidate = Path(row["candidate_file"])
    latent_path = latent_root / f"seed_{seed}.npz"
    if sha(source) != row["source_sha256"] or sha(candidate) != row["candidate_sha256"]:
        raise ValueError(f"source contract mismatch for {seed}")
    with np.load(source, allow_pickle=False) as src, np.load(candidate, allow_pickle=False) as cand, \
            np.load(latent_path, allow_pickle=False) as lat:
        actions = cand["candidate_actions"].astype(np.float32)
        selected = cand["selected_index"].astype(np.int64)
        if len(actions) != len(selected) or lat["latent_states"].shape != (len(actions) + 1, 9216):
            raise ValueError(f"shape mismatch for {seed}")
        committed = src["action_chunks"].astype(np.float32)
        if not np.array_equal(actions[np.arange(len(actions)), selected], committed):
            raise ValueError(f"selected/committed mismatch for {seed}")
        steps = np.append(src["replan_steps"], int(src["final_steps"])).astype(np.float32)
        remaining = (1.0 - steps / int(src["task_limit"]))[:, None]
        aux = np.concatenate([src["joint_positions"], src["tcp_pose"], remaining], axis=1).astype(np.float32)
        states = np.concatenate([lat["latent_states"].astype(np.float32), aux], axis=1)
        deviations = actions - actions.mean(axis=1, keepdims=True)
        spread = np.sqrt(np.mean(np.square(deviations), axis=1, keepdims=True))
        action_features = np.concatenate([deviations, np.broadcast_to(spread, deviations.shape)], axis=-1)
        return {
            "states": states[:-1], "action_features": action_features,
            "selected": selected, "rewards": src["rewards"].astype(np.float32),
            "executed_steps": src["executed_steps"].astype(np.int64),
            "terminal": src["finite_horizon_terminal"].astype(bool),
        }


def equal_episode_scaler(episodes, key, floor):
    means = np.stack([episode[key].mean(axis=tuple(range(episode[key].ndim - 1))) for episode in episodes])
    seconds = np.stack([(episode[key] ** 2).mean(axis=tuple(range(episode[key].ndim - 1))) for episode in episodes])
    mean = means.mean(axis=0).astype(np.float32)
    variance = np.maximum(seconds.mean(axis=0) - mean ** 2, floor ** 2)
    return mean, np.sqrt(variance).astype(np.float32)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    root = args.stage / "v5_candidate_centered_v1"
    out = root / "data"
    if out.exists():
        raise FileExistsError(out)
    audit_path = root / "candidate_audit.json"
    audit = json.loads(audit_path.read_text())
    if not audit.get("valid") or len(audit["episodes"]) != 32:
        raise ValueError("v5 candidate audit is not admitted")
    latent_root = args.stage / "v4_unitas_latents_v1"
    rows = audit["episodes"]
    arrays = {int(row["seed"]): episode_arrays(row, latent_root) for row in rows}
    out.mkdir(parents=True)
    folds = []
    for fold in range(4):
        train_rows = [row for row in rows if int(row["fold"]) != fold]
        val_rows = [row for row in rows if int(row["fold"]) == fold]
        if (len(train_rows), len(val_rows)) != (24, 8):
            raise ValueError(f"fold {fold} is not 24/8")
        train = [arrays[int(row["seed"])] for row in train_rows]
        state_mean, state_scale = equal_episode_scaler(train, "states", 1e-5)
        action_mean, action_scale = equal_episode_scaler(train, "action_features", 1e-5)
        scaler = out / f"scaler_fold{fold}.npz"
        np.savez(scaler, state_mean=state_mean, state_scale=state_scale,
                 action_mean=action_mean, action_scale=action_scale)
        folds.append({
            "fold": fold,
            "train": [{"seed": int(row["seed"]), "success": bool(row["success"])} for row in train_rows],
            "validation": [{"seed": int(row["seed"]), "success": bool(row["success"])} for row in val_rows],
            "scaler_file": scaler.name, "scaler_sha256": sha(scaler),
        })
    manifest = {
        "schema": "qgf_v5_candidate_centered_data_v1", "episodes": 32,
        "state_dim": 9269, "candidate_shape": [4, 10, 32],
        "source_audit_sha256": sha(audit_path), "folds": folds,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "COMPLETE").touch()
    print(json.dumps({"status": "COMPLETE", "manifest_sha256": sha(manifest_path)}))


if __name__ == "__main__":
    main()
