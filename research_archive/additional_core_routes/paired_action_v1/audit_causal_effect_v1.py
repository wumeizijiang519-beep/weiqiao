#!/usr/bin/env python3
"""Read-only causal effect audit for the frozen boundary-anchored dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np


EPS = 1e-6


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pairwise(values: np.ndarray, reducer) -> list[float]:
    return [float(reducer(values[i] - values[j])) for i, j in combinations(range(len(values)), 2)]


def locate_episode(roots: list[Path], episode_id: str) -> Path:
    matches = [root / episode_id for root in roots if (root / episode_id / "GROUP_COMPLETE").is_file()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one completed source for {episode_id}, found {matches}")
    return matches[0]


def audit_group(root: Path, group: dict) -> dict:
    bank_path = root / "bank.npz"
    with np.load(bank_path, allow_pickle=False) as bank:
        actions = np.asarray(bank["candidates_native"], dtype=np.float64)
        boundary = np.asarray(bank["boundary_state"], dtype=np.float64)
    if actions.shape != (4, 32, 7) or not np.isfinite(actions).all():
        raise RuntimeError(f"Invalid candidate bank for {group['episode_id']}: {actions.shape}")

    trajectories = []
    results = []
    for candidate in range(4):
        trajectory_path = root / f"candidate_{candidate}" / "trajectory.npz"
        result_path = root / f"candidate_{candidate}" / "result.json"
        with np.load(trajectory_path, allow_pickle=False) as trajectory:
            action_prefix = np.asarray(trajectory["actions"], dtype=np.float64)
            states = np.asarray(trajectory["sim_states"], dtype=np.float64)
            rewards = np.asarray(trajectory["rewards"], dtype=np.float64)
            success = np.asarray(trajectory["success"], dtype=bool)
        if action_prefix.shape != (10, 7) or states.shape != (10, boundary.size):
            raise RuntimeError(f"Invalid trajectory for {group['episode_id']} candidate {candidate}")
        if not np.array_equal(action_prefix, actions[candidate, :10]):
            raise RuntimeError(f"Committed action mismatch for {group['episode_id']} candidate {candidate}")
        trajectories.append((action_prefix, states, rewards, success))
        results.append(json.loads(result_path.read_text(encoding="utf-8")))

    prefixes = np.stack([item[0] for item in trajectories])
    endpoints = np.stack([item[1][-1] for item in trajectories])
    state_paths = np.stack([item[1] for item in trajectories])
    returns = np.asarray([item[2].sum() for item in trajectories], dtype=np.float64)
    successes = np.asarray([item[3].any() for item in trajectories], dtype=bool)
    goal_fractions = np.asarray([item["final_goal_fraction"] for item in results], dtype=np.float64)

    action_mad = pairwise(prefixes, lambda delta: np.mean(np.abs(delta)))
    action_l2 = pairwise(prefixes, lambda delta: np.linalg.norm(delta))
    endpoint_l2 = pairwise(endpoints, lambda delta: np.linalg.norm(delta))
    endpoint_max = pairwise(endpoints, lambda delta: np.max(np.abs(delta)))
    path_l2 = pairwise(state_paths, lambda delta: np.linalg.norm(delta))
    boundary_effect_l2 = [float(np.linalg.norm(endpoint - boundary)) for endpoint in endpoints]

    action_diverse = min(action_l2) > EPS
    physically_divergent = max(endpoint_max) > EPS
    feedback_divergent = (
        len(set(successes.tolist())) > 1
        or np.ptp(returns) > EPS
        or np.ptp(goal_fractions) > EPS
    )
    if not action_diverse:
        classification = "NO_ACTION_DIVERSITY"
    elif not physically_divergent:
        classification = "NO_PHYSICAL_EFFECT"
    elif not feedback_divergent:
        classification = "PHYSICAL_DIVERGENCE_WITH_FEEDBACK_INSENSITIVITY"
    else:
        classification = "IDENTIFIABLE_FEEDBACK_EFFECT"

    return {
        "episode_id": group["episode_id"],
        "family": group["family"],
        "classification": classification,
        "action_prefix_pairwise_mad": action_mad,
        "action_prefix_pairwise_l2": action_l2,
        "endpoint_state_pairwise_l2": endpoint_l2,
        "endpoint_state_pairwise_max_abs": endpoint_max,
        "state_path_pairwise_l2": path_l2,
        "boundary_to_endpoint_l2": boundary_effect_l2,
        "returns": returns.tolist(),
        "successes": successes.tolist(),
        "goal_fractions": goal_fractions.tolist(),
        "source_hashes": {
            "bank": sha256(bank_path),
            "trajectories": [
                sha256(root / f"candidate_{candidate}" / "trajectory.npz") for candidate in range(4)
            ],
        },
    }


def summary(values: list[float]) -> dict:
    array = np.asarray(values, dtype=np.float64)
    return {
        "min": float(array.min()),
        "median": float(np.median(array)),
        "mean": float(array.mean()),
        "max": float(array.max()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-report", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--remaining-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    final_report = json.loads(args.final_report.read_text(encoding="utf-8"))
    if final_report.get("status") != "NO_PAIRED_ACTION_VALUE_SIGNAL":
        raise RuntimeError("Unexpected frozen source result")
    roots = [args.pilot_root, args.remaining_root]
    groups = [audit_group(locate_episode(roots, item["episode_id"]), item) for item in final_report["results"]]

    classifications: dict[str, int] = {}
    for group in groups:
        key = group["classification"]
        classifications[key] = classifications.get(key, 0) + 1
    report = {
        "status": "CAUSAL_EFFECT_AUDIT_COMPLETE",
        "read_only": True,
        "groups": len(groups),
        "classification_counts": classifications,
        "aggregate": {
            "action_prefix_pairwise_mad": summary(
                [value for group in groups for value in group["action_prefix_pairwise_mad"]]
            ),
            "endpoint_state_pairwise_l2": summary(
                [value for group in groups for value in group["endpoint_state_pairwise_l2"]]
            ),
            "endpoint_state_pairwise_max_abs": summary(
                [value for group in groups for value in group["endpoint_state_pairwise_max_abs"]]
            ),
            "state_path_pairwise_l2": summary(
                [value for group in groups for value in group["state_path_pairwise_l2"]]
            ),
        },
        "source_final_report_sha256": sha256(args.final_report),
        "results": groups,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("status", "groups", "classification_counts", "aggregate")}, indent=2))


if __name__ == "__main__":
    main()
