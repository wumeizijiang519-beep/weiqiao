"""Capture one fresh initial observation and audit a native N16 diverse bank."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unitas_robotwin_candidate_client import CandidatePolicyClient
import unitas_robotwin_gate_client as base
import trajectory_collector


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairwise_l1(chunks):
    values = []
    for left in range(len(chunks)):
        for right in range(left + 1, len(chunks)):
            values.append(float(np.mean(np.abs(chunks[left] - chunks[right]))))
    return float(np.mean(values))


def farthest_subset(normalized):
    selected = [0]
    while len(selected) < 4:
        scores = []
        for index in range(len(normalized)):
            if index in selected:
                scores.append(-1.0)
                continue
            distances = [float(np.mean(np.abs(normalized[index] - normalized[other]))) for other in selected]
            scores.append(min(distances))
        selected.append(int(np.argmax(scores)))
    return selected


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--probe-output", type=Path, required=True)
    parser.add_argument("--scaler", type=Path, required=True)
    known, remaining = parser.parse_known_args()
    known.probe_output.mkdir(parents=True, exist_ok=False)
    with np.load(known.scaler, allow_pickle=False) as raw:
        scale = raw["action_scale"].astype(np.float32)
    if scale.shape != (16,) or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("invalid frozen action scaler")

    class ProbeClient(CandidatePolicyClient):
        def act(self, observation, instruction, history):
            if history:
                raise ValueError("zero-action probe must start at the initial observation")
            started = time.monotonic()
            candidates, server_diversity = self.candidates(observation, instruction, history, 16)
            normalized = candidates / scale[None, None, :]
            subset = farthest_subset(normalized)
            baseline = [0, 1, 2, 3]
            commits = []
            errors = []
            for index in subset:
                self.reset()
                committed = self.commit_candidate(observation, instruction, history, index)
                commits.append(committed)
                errors.append(float(np.max(np.abs(committed - candidates[index]))))
            self.reset()
            baseline_l1 = pairwise_l1(normalized[baseline])
            subset_l1 = pairwise_l1(normalized[subset])
            ratio = subset_l1 / max(baseline_l1, 1e-12)
            report = {
                "schema": "qgf_v6_zero_action_probe_v1", "executed_policy_actions": 0,
                "candidate_count": 16, "subset_indices": subset,
                "baseline_pairwise_normalized_l1": baseline_l1,
                "subset_pairwise_normalized_l1": subset_l1, "diversity_ratio": ratio,
                "selected_commit_max_error": max(errors),
                "all_finite": bool(np.isfinite(candidates).all()),
                "subset_nonidentical": bool(subset_l1 > 0),
                "candidate0_preserved": subset[0] == 0,
                "scaler_sha256": sha(known.scaler), "server_diversity": server_diversity,
                "latency_seconds": time.monotonic() - started,
            }
            np.savez_compressed(known.probe_output / "arrays.npz", candidates=candidates,
                                subset_indices=np.asarray(subset), commits=np.asarray(commits))
            (known.probe_output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
            (known.probe_output / "COMPLETE").touch()
            raise SystemExit(0)

    base.PolicyClient = ProbeClient
    sys.argv = [sys.argv[0], *remaining]
    trajectory_collector.main()


if __name__ == "__main__":
    main()
