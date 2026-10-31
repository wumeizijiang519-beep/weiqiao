"""Prepare the frozen 24/8 QGF-v4 intervention split and UNITAS features."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from features import training_scaler


SALT = "qgf-v4-intervention-split-v1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def order(seed):
    return hashlib.sha256(f"{SALT}:{seed}".encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    audit_path = args.stage / "v4_intervention_train32_v1" / "summary.json"
    latent_root = args.stage / "v4_unitas_latents_v1"
    output = args.stage / "v4_critic_v1" / "data"
    if output.exists():
        raise FileExistsError(output)
    audit = json.loads(audit_path.read_text())
    latent_manifest = json.loads((latent_root / "manifest.json").read_text())
    if not audit.get("admits_critic_training") or len(audit["episodes"]) != 32:
        raise ValueError("Train32 is not admitted")
    if latent_manifest.get("episodes") != 32 or latent_manifest.get("source_audit_sha256") != sha(audit_path):
        raise ValueError("latent/source contract mismatch")

    failures = sorted((row for row in audit["episodes"] if not row["success"]), key=lambda row: order(row["seed"]))
    successes = sorted((row for row in audit["episodes"] if row["success"]), key=lambda row: order(row["seed"]))
    validation_seeds = {int(row["seed"]) for row in failures[:2] + successes[:6]}
    partitions = {
        "train": [row for row in audit["episodes"] if int(row["seed"]) not in validation_seeds],
        "validation": [row for row in audit["episodes"] if int(row["seed"]) in validation_seeds],
    }
    counts = {name: {"episodes": len(rows), "successes": sum(bool(row["success"]) for row in rows),
                     "failures": sum(not bool(row["success"]) for row in rows)} for name, rows in partitions.items()}
    if counts != {"train": {"episodes": 24, "successes": 19, "failures": 5},
                  "validation": {"episodes": 8, "successes": 6, "failures": 2}}:
        raise ValueError(f"frozen split contract failed: {counts}")

    output.mkdir(parents=True)
    cache = {}
    for record in audit["episodes"]:
        seed = int(record["seed"])
        source_path = Path(record["file"])
        if sha(source_path) != record["sha256"]:
            raise ValueError(f"source SHA mismatch for {seed}")
        latent_path = latent_root / f"seed_{seed}.npz"
        with np.load(source_path, allow_pickle=False) as src, np.load(latent_path, allow_pickle=False) as lat:
            chunks = len(src["action_chunks"])
            latent = np.asarray(lat["latent_states"], dtype=np.float32)
            if latent.shape != (chunks + 1, 9216):
                raise ValueError(f"latent shape mismatch for {seed}: {latent.shape}")
            steps = np.append(src["replan_steps"], int(src["final_steps"])).astype(np.float32)
            remaining = (1 - steps / int(src["task_limit"]))[:, None]
            aux = np.concatenate([src["joint_positions"], src["tcp_pose"], remaining], axis=1).astype(np.float32)
            arrays = {"states": np.concatenate([latent, aux], axis=1).astype(np.float32),
                "actions": src["action_chunks"].astype(np.float32), "rewards": src["rewards"].astype(np.float32),
                "steps": src["executed_steps"].astype(np.int64), "terminal": src["finite_horizon_terminal"].astype(bool),
                "seed": np.asarray(seed), "success": np.asarray(bool(record["success"]))}
        cache[seed] = arrays

    manifest = {"schema": "qgf_v4_intervention_critic_data_v1", "split_salt": SALT,
        "source_audit_sha256": sha(audit_path), "latent_manifest_sha256": sha(latent_root / "manifest.json"),
        "state_dim": 9269, "action_shape": [10, 16], "counts": counts, "partitions": {}}
    for name, records in partitions.items():
        manifest["partitions"][name] = []
        for record in records:
            seed = int(record["seed"])
            path = output / f"{name}_{seed}.npz"
            np.savez_compressed(path, **cache[seed])
            manifest["partitions"][name].append({"seed": seed, "success": bool(record["success"]),
                "source_sha256": record["sha256"], "feature_file": path.name, "feature_sha256": sha(path)})
    train = [cache[int(row["seed"])] for row in partitions["train"]]
    scaler_path = output / "training_scaler.npz"
    np.savez(scaler_path, **training_scaler(train))
    manifest["scaler_sha256"] = sha(scaler_path)
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "COMPLETE").touch()
    print(json.dumps({"status": "COMPLETE", "counts": counts, "manifest_sha256": sha(manifest_path)}))


if __name__ == "__main__":
    main()

