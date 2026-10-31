"""Freeze an episode-equal action scale from v4 training-only trajectories."""

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    audit = json.loads((ROOT / "v5_candidate_centered_v1" / "candidate_audit.json").read_text())
    means, seconds = [], []
    for row in audit["episodes"]:
        with np.load(row["source_file"], allow_pickle=False) as raw:
            actions = raw["action_chunks"].astype(np.float64).reshape(-1, 16)
        means.append(actions.mean(axis=0))
        seconds.append(np.square(actions).mean(axis=0))
    mean = np.mean(means, axis=0)
    scale = np.sqrt(np.maximum(np.mean(seconds, axis=0) - np.square(mean), 1e-10))
    output = ROOT / "v6_diverse_bank_v1" / "action_scaler.npz"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    np.savez(output, action_mean=mean.astype(np.float32), action_scale=scale.astype(np.float32),
             source_audit_sha256=np.asarray(sha(ROOT / "v5_candidate_centered_v1" / "candidate_audit.json")))
    print(json.dumps({"path": str(output), "sha256": sha(output), "episodes": 32}))


if __name__ == "__main__":
    main()
