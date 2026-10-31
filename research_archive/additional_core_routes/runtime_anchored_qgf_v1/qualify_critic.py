"""Independent OOF qualification for Runtime-Anchored critic."""

import argparse
import json
from pathlib import Path

import numpy as np

SEEDS = (202642301, 202642302, 202642303)


def bootstrap(values, seed, draws=10000):
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    sampled = values[rng.integers(0, len(values), size=(draws, len(values)))].mean(1)
    return np.quantile(sampled, [0.025, 0.975]).tolist()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    per_seed = []
    deltas_state = {g: [] for g in range(12)}
    deltas_perm = {g: [] for g in range(12)}
    missing_by_seed = {}
    for seed in SEEDS:
        group_scores = {name: {} for name in ("action_aware", "state_only", "permutation")}
        sensitivities = []
        for fold in range(3):
            run = args.runs / f"seed_{seed}_fold_{fold}"
            report = json.loads((run / "REPORT.json").read_text())
            if report["status"] != "RUNTIME_ANCHORED_CRITIC_WORKER_COMPLETE":
                raise RuntimeError("Worker incomplete")
            with np.load(run / "HELD_PREDICTIONS.npz") as saved:
                target = saved["target"]
                groups = saved["group_index"]
                sensitivities.extend((saved["sensitivity"] > 1e-7).tolist())
                for group in np.unique(groups):
                    mask = groups == group
                    for name in group_scores:
                        pred = saved[name][mask]
                        group_scores[name][int(group)] = float(np.mean((pred > 0) == (target[mask] > 0.5)))
        covered = sorted(set.intersection(*(set(values) for values in group_scores.values())))
        missing = sorted(set(range(12)) - set(covered))
        missing_by_seed[str(seed)] = missing
        means = {name: float(np.mean([values[g] for g in covered])) for name, values in group_scores.items()}
        for group in range(12):
            if group in covered:
                deltas_state[group].append(group_scores["action_aware"][group] - group_scores["state_only"][group])
                deltas_perm[group].append(group_scores["action_aware"][group] - group_scores["permutation"][group])
            else:
                deltas_state[group].append(0.0)
                deltas_perm[group].append(0.0)
        per_seed.append({"seed": seed, "group_equal_accuracy": means,
                         "action_sensitivity_fraction": float(np.mean(sensitivities)),
                         "beats_state_only": means["action_aware"] > means["state_only"],
                         "beats_permutation": means["action_aware"] > means["permutation"]})
    state_ci = bootstrap([np.mean(deltas_state[g]) for g in range(12)], 202642401)
    perm_ci = bootstrap([np.mean(deltas_perm[g]) for g in range(12)], 202642402)
    complete_coverage = all(not value for value in missing_by_seed.values())
    admitted = (complete_coverage
                and all(row["beats_state_only"] and row["beats_permutation"] and
                    row["action_sensitivity_fraction"] >= 0.9 for row in per_seed)
                and state_ci[0] > 0 and perm_ci[0] > 0)
    result = {"status": "RUNTIME_ANCHORED_CRITIC_ADMIT" if admitted else "NO_STABLE_RUNTIME_ANCHORED_CRITIC",
              "per_seed": per_seed, "state_only_delta_ci95": state_ci,
              "permutation_delta_ci95": perm_ci, "bootstrap_draws": 10000,
              "missing_informative_groups_by_seed": missing_by_seed,
              "complete_group_coverage": complete_coverage,
              "online_qgf_efficacy": None}
    args.output.parent.mkdir(parents=True, exist_ok=False)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.output.parent / result["status"]).touch()


if __name__ == "__main__":
    main()
