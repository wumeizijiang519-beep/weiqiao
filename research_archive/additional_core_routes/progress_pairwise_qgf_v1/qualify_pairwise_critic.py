"""Independent OOF qualification for the three-seed pairwise critic."""

import argparse
import json
from pathlib import Path

import numpy as np


SEEDS = (202641601, 202641602, 202641603)


def accuracy(logit, target):
    correct = ((logit > 0) == (target > .5)).astype(np.float64)
    correct[np.abs(logit) <= 1e-8] = .5
    return correct


def bootstrap(values, seed=202641701, draws=10000):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    sample = values[rng.integers(0, len(values), size=(draws, len(values)))].mean(1)
    return [float(np.quantile(sample, .025)), float(np.quantile(sample, .975))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text())
    per_seed, group_deltas_state, group_deltas_permutation = [], {}, {}
    for seed in SEEDS:
        groups = {}
        sensitivity = []
        held_group_inventory = []
        for fold in range(4):
            run = args.runs / f"seed_{seed}_fold_{fold}"
            report = json.loads((run / "REPORT.json").read_text())
            if (report["status"] != "PAIRWISE_CRITIC_WORKER_COMPLETE_NOT_QUALIFICATION"
                    or report["seed"] != seed or report["held_fold"] != fold
                    or report["updates"] != 3000 or not (run / "WORKER_COMPLETE").exists()):
                raise RuntimeError("Incomplete frozen pairwise worker")
            with np.load(run / "HELD_PREDICTIONS.npz", allow_pickle=False) as data:
                target = data["target"]
                held_group_inventory.extend(data["group_index"].tolist())
                sensitivity.extend((data["sensitivity"] > 1e-6).tolist())
                for group in np.unique(data["group_index"]):
                    index = data["group_index"] == group
                    groups[int(group)] = {name: float(accuracy(data[name][index], target[index]).mean())
                                          for name in ("action_aware", "state_only", "permutation")}
        # A scientific-denominator group may contain no non-tied horizon-32
        # comparisons. It stays in the OOF analysis as zero evidence rather
        # than being silently dropped or assigned a fabricated preference.
        for group in range(14):
            groups.setdefault(group, {name: .5 for name in
                ("action_aware", "state_only", "permutation")})
        means = {name: float(np.mean([row[name] for row in groups.values()]))
                 for name in ("action_aware", "state_only", "permutation")}
        row = {"seed": seed, "group_equal_accuracy": means,
               "action_sensitivity_fraction": float(np.mean(sensitivity)),
               "beats_state_only": means["action_aware"] > means["state_only"],
               "beats_permutation": means["action_aware"] > means["permutation"]}
        per_seed.append(row)
        for group, values in groups.items():
            group_deltas_state.setdefault(group, []).append(values["action_aware"] - values["state_only"])
            group_deltas_permutation.setdefault(group, []).append(values["action_aware"] - values["permutation"])
    state_values = [np.mean(group_deltas_state[g]) for g in range(14)]
    permutation_values = [np.mean(group_deltas_permutation[g]) for g in range(14)]
    state_ci = bootstrap(state_values)
    permutation_ci = bootstrap(permutation_values)
    admitted = (all(row["beats_state_only"] and row["beats_permutation"]
                    and row["action_sensitivity_fraction"] >= .9 for row in per_seed)
                and state_ci[0] > 0 and permutation_ci[0] > 0)
    result = {"status": "PAIRWISE_CRITIC_QUALIFIED" if admitted else "NO_STABLE_PROGRESS_PAIRWISE_CRITIC",
              "per_seed": per_seed,
              "state_only_delta_ci95": state_ci,
              "permutation_delta_ci95": permutation_ci,
              "bootstrap_seed": 202641701, "bootstrap_draws": 10000,
              "physical_groups": 14, "gpu_workers": 12,
              "online_qgf_efficacy": None}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()
