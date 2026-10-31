"""Audit and index the retained N=4 candidate sets from QGF-v4 Train32."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


RUNS = [
    "v4_intervention_train32_shard0",
    "v4_intervention_train32_shard1",
    "v4_intervention_train32_shard2",
    "v4_intervention_train32_shard3_retry1",
]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    args = parser.parse_args()
    output = args.stage / "v5_candidate_centered_v1"
    output.mkdir(exist_ok=True)
    episodes = []
    all_pair_means = []
    selected_counts = np.zeros(4, dtype=np.int64)
    for fold, run_name in enumerate(RUNS):
        run = args.stage / "runs" / run_name
        audit = json.loads((run / "audit.json").read_text())
        if not audit.get("valid") or len(audit["episodes"]) != 8:
            raise ValueError(f"invalid source shard: {run}")
        rows = [json.loads(line) for line in (run / "selection.jsonl").read_text().splitlines() if line.strip()]
        expected_rows = sum(int(row["replans"]) for row in audit["episodes"])
        if len(rows) != expected_rows:
            raise ValueError(f"selection segmentation mismatch for {run_name}: {len(rows)} != {expected_rows}")
        cursor = 0
        for episode in audit["episodes"]:
            source = Path(episode["file"])
            if sha(source) != episode["sha256"]:
                raise ValueError(f"source SHA mismatch: {source}")
            with np.load(source, allow_pickle=False) as data:
                actions = np.asarray(data["action_chunks"], dtype=np.float32)
                count = len(actions)
                segment = rows[cursor:cursor + count]
                cursor += count
                candidates = np.asarray([row["candidate_actions"] for row in segment], dtype=np.float32)
                selected = np.asarray([row["selected_index"] for row in segment], dtype=np.int64)
                if candidates.shape != (count, 4, 10, 16) or not np.isfinite(candidates).all():
                    raise ValueError(f"candidate tensor contract failed for {source}")
                committed = candidates[np.arange(count), selected]
                error = float(np.max(np.abs(committed - actions))) if count else 0.0
                if error > 1e-6:
                    raise ValueError(f"selected action mismatch {error}: {source}")
                selected_counts += np.bincount(selected, minlength=4)
                centered = candidates - candidates.mean(axis=1, keepdims=True)
                all_pair_means.append(float(np.mean(np.abs(centered))))
                candidate_file = output / f"candidates_seed{int(episode['seed'])}.npz"
                if candidate_file.exists():
                    raise FileExistsError(candidate_file)
                np.savez_compressed(candidate_file, candidate_actions=candidates, selected_index=selected)
                episodes.append({"fold": fold, "seed": int(episode["seed"]), "success": bool(episode["success"]),
                    "replans": count, "source_file": str(source), "source_sha256": episode["sha256"],
                    "candidate_file": str(candidate_file), "candidate_sha256": sha(candidate_file),
                    "selected_commit_max_error": error})
    if len(episodes) != 32 or len({row["seed"] for row in episodes}) != 32:
        raise ValueError("expected 32 unique episodes")
    result = {"schema": "qgf_v5_candidate_set_audit_v1", "valid": True, "episodes": episodes,
        "selected_counts": selected_counts.tolist(), "mean_within_set_abs_deviation": float(np.mean(all_pair_means)),
        "source_runs": RUNS}
    path = output / "candidate_audit.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    (output / "AUDIT_COMPLETE").touch()
    print(json.dumps({"episodes": 32, "selected_counts": result["selected_counts"],
        "mean_within_set_abs_deviation": result["mean_within_set_abs_deviation"], "audit_sha256": sha(path)}))


if __name__ == "__main__":
    main()
